"""Luci data updater."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from functools import cached_property
from typing import Final

from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant, CALLBACK_TYPE
from homeassistant.helpers import event
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import json
from homeassistant.util import utcnow
from httpx import codes

from .const import (
    DOMAIN,
    UPDATER,
    SIGNAL_NEW_DEVICE,
    DEFAULT_RETRY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_ACTIVITY_DAYS,
    DEFAULT_NAME,
    DEFAULT_MANUFACTURER,
    DEFAULT_CALL_DELAY,
    ATTR_STATE,
    ATTR_DEVICE_MODEL,
    ATTR_DEVICE_MANUFACTURER,
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_DEVICE_NAME,
    ATTR_DEVICE_SW_VERSION,
    ATTR_BINARY_SENSOR_WAN_STATE,
    ATTR_BINARY_SENSOR_DUAL_BAND,
    ATTR_SENSOR_UPTIME,
    ATTR_SENSOR_MEMORY_USAGE,
    ATTR_SENSOR_MEMORY_TOTAL,
    ATTR_SENSOR_TEMPERATURE,
    ATTR_SENSOR_MODE,
    ATTR_SENSOR_DEVICES,
    ATTR_SENSOR_DEVICES_LAN,
    ATTR_SENSOR_DEVICES_GUEST,
    ATTR_SENSOR_DEVICES_2_4,
    ATTR_SENSOR_DEVICES_5_0,
    ATTR_SENSOR_DEVICES_5_0_GAME,
    ATTR_LIGHT_LED,
    ATTR_WIFI_ADAPTER_LENGTH,
    ATTR_TRACKER_ENTRY_ID,
    ATTR_TRACKER_UPDATER_ENTRY_ID,
    ATTR_TRACKER_MAC,
    ATTR_TRACKER_ROUTER_MAC_ADDRESS,
    ATTR_TRACKER_SIGNAL,
    ATTR_TRACKER_NAME,
    ATTR_TRACKER_CONNECTION,
    ATTR_TRACKER_IP,
    ATTR_TRACKER_ONLINE,
    ATTR_TRACKER_LAST_ACTIVITY,
    ATTR_TRACKER_DOWN_SPEED,
    ATTR_TRACKER_UP_SPEED,
)
from .enum import (
    Mode,
    Connection,
    IfName,
    DeviceAction,
)
from .exceptions import LuciConnectionException, LuciTokenException
from .luci import LuciClient

PREPARE_METHODS: Final = [
    "init",
    "status",
    "mode",
    "wan",
    "led",
    "wifi",
    "devices",
    "device_list",
    "new_status",
]

_LOGGER = logging.getLogger(__name__)


class LuciUpdater(DataUpdateCoordinator):
    """Luci data updater for interaction with Luci API."""

    luci: LuciClient
    code: codes = codes.BAD_GATEWAY
    ip: str
    new_device_callback: CALLBACK_TYPE | None = None
    is_force_load: bool = False

    _manufacturers: dict[str, str] = {}

    _store: Store | None = None

    _scan_interval: int
    _activity_days: int
    _is_only_login: bool = False
    _is_reauthorization: bool = True

    _signals: dict[str, int] = {}
    _moved_devices: list = []

    def __init__(
        self,
        hass: HomeAssistant,
        ip: str,
        password: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        timeout: int = DEFAULT_TIMEOUT,
        is_force_load: bool = False,
        activity_days: int = DEFAULT_ACTIVITY_DAYS,
        store: Store | None = None,
        is_only_login: bool = False,
    ) -> None:
        """Initialize updater.

        :rtype: object
        :param hass: HomeAssistant: Home Assistant object
        :param ip: str: device ip address
        :param password: str: device password
        :param scan_interval: int: Update interval
        :param timeout: int: Query execution timeout
        :param is_force_load: bool: Force boot devices when using repeater and mesh mode
        :param activity_days: int: Allowed number of days to wait after the last activity
        :param store: Store | None: Device store
        :param is_only_login: bool: Only config flow
        """

        self.luci = LuciClient(get_async_client(hass, False), ip, password, timeout)

        self.ip = ip
        self.is_force_load = is_force_load

        self._store = store

        self._scan_interval = scan_interval
        self._activity_days = activity_days
        self._is_only_login = is_only_login

        if hass is not None:
            super().__init__(
                hass,
                _LOGGER,
                name=f"MiWifi updater",
                update_interval=self.update_interval,
                update_method=self.update,
            )

        self.data = {}
        self.devices: dict = {}

        hass.loop.call_later(
            DEFAULT_CALL_DELAY,
            lambda: hass.async_create_task(self._async_load_manufacturers()),
        )

        hass.async_create_task(self._async_load_devices())

    async def async_stop(self) -> None:
        """Stop updater"""

        if self.new_device_callback is not None:
            self.new_device_callback()

        await self._async_save_devices()
        await self.luci.logout()

    @cached_property
    def update_interval(self) -> timedelta:
        """Update interval

        :return timedelta: update_interval
        """

        return timedelta(seconds=self._scan_interval)

    async def update(self, is_force: bool = False, retry: int = 1) -> dict:
        """Update miwifi information.

        :param is_force: bool: Force relogin
        :param retry: int: Retry count
        :return dict: dict with luci data.
        """

        err: LuciConnectionException | LuciTokenException | None = None

        try:
            if self._is_reauthorization or self._is_only_login or is_force:
                if is_force:
                    await self.luci.logout()
                    await asyncio.sleep(DEFAULT_CALL_DELAY)

                await self.luci.login()

            self.code = codes.OK

            if not self._is_only_login or is_force:
                for method in PREPARE_METHODS:
                    await self._async_prepare(method, self.data)
        except LuciConnectionException as e:
            err = e

            self._is_reauthorization = False
            self.code = codes.NOT_FOUND
        except LuciTokenException as e:
            err = e

            self._is_reauthorization = True
            self.code = codes.FORBIDDEN

        self.data[ATTR_STATE] = codes.is_success(self.code)

        if is_force and retry <= DEFAULT_RETRY and not self.data[ATTR_STATE]:
            _LOGGER.error(
                "Error connecting to router (attempt #%s of %s): %r",
                retry,
                DEFAULT_RETRY,
                err,
            )

            await asyncio.sleep(retry)

            return await self.update(True, retry + 1)

        if not self._is_only_login:
            self._clean_devices()

        return self.data

    @property
    def is_repeater(self) -> bool:
        """Is repeater property

        :return bool: is_repeater
        """

        return self.data.get(ATTR_SENSOR_MODE, Mode.DEFAULT).value > 0

    @property
    def device_info(self):
        """Device info.

        :return DeviceInfo: Service DeviceInfo.
        """

        return DeviceInfo(
            identifiers={(DOMAIN, self.data.get(ATTR_DEVICE_MAC_ADDRESS, self.ip))},
            connections={
                (
                    CONNECTION_NETWORK_MAC,
                    self.data.get(ATTR_DEVICE_MAC_ADDRESS, self.ip),
                )
            },
            name=self.data.get(ATTR_DEVICE_NAME, DEFAULT_NAME),
            manufacturer=self.data.get(ATTR_DEVICE_MANUFACTURER, DEFAULT_MANUFACTURER),
            model=self.data.get(ATTR_DEVICE_MODEL, None),
            sw_version=self.data.get(ATTR_DEVICE_SW_VERSION, None),
            configuration_url=f"http://{self.ip}/",
        )

    def schedule_refresh(self, offset: timedelta) -> None:
        """Schedule refresh.

        :param offset: timedelta
        """

        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None

        self._unsub_refresh = event.async_track_point_in_utc_time(
            self.hass,
            self._job,
            utcnow().replace(microsecond=0) + offset,
        )

    async def _async_prepare(self, method: str, data: dict) -> None:
        """Prepare data.

        :param method: str
        :param data: dict
        """

        action = getattr(self, f"_async_prepare_{method}")

        if action:
            await action(data)

    async def _async_prepare_init(self, data: dict) -> None:
        """Prepare init info.

        :param data: dict
        """

        response: dict = await self.luci.init_info()

        if "model" in response:
            data[ATTR_DEVICE_MODEL] = response["model"]

            manufacturer: list = response["model"].split(".")
            data[ATTR_DEVICE_MANUFACTURER] = manufacturer[0].title()
        elif "hardware" in response:
            data[ATTR_DEVICE_MODEL] = response["hardware"]

        if "routername" in response:
            data[ATTR_DEVICE_NAME] = response["routername"]

        if "romversion" in response and "countrycode" in response:
            data[
                ATTR_DEVICE_SW_VERSION
            ] = f"{response['romversion']} ({response['countrycode']})"

    async def _async_prepare_status(self, data: dict) -> None:
        """Prepare status.

        :param data: dict
        """

        response: dict = await self.luci.status()

        if (
            "hardware" in response
            and isinstance(response["hardware"], dict)
            and "mac" in response["hardware"]
        ):
            data[ATTR_DEVICE_MAC_ADDRESS] = response["hardware"]["mac"]

        if "upTime" in response:
            data[ATTR_SENSOR_UPTIME] = str(
                timedelta(seconds=int(float(response["upTime"])))
            )

        if "mem" in response and isinstance(response["mem"], dict):
            if "usage" in response["mem"]:
                data[ATTR_SENSOR_MEMORY_USAGE] = int(
                    float(response["mem"]["usage"]) * 100
                )

            if "total" in response["mem"]:
                data[ATTR_SENSOR_MEMORY_TOTAL] = int(
                    "".join(i for i in response["mem"]["total"] if i.isdigit())
                )

        if "temperature" in response:
            data[ATTR_SENSOR_TEMPERATURE] = float(response["temperature"])

    async def _async_prepare_mode(self, data: dict) -> None:
        """Prepare mode.

        :param data: dict
        """

        if data.get(ATTR_SENSOR_MODE, Mode.DEFAULT) == Mode.MESH:
            return

        response: dict = await self.luci.mode()

        if "mode" in response:
            data[ATTR_SENSOR_MODE] = Mode(int(response["mode"]))

    async def _async_prepare_wan(self, data: dict) -> None:
        """Prepare mode.

        :param data: dict
        """

        response: dict = await self.luci.wan_info()

        if (
            "info" in response
            and isinstance(response["info"], dict)
            and "uptime" in response["info"]
        ):
            data[ATTR_BINARY_SENSOR_WAN_STATE] = response["info"]["uptime"] > 0
        else:
            data[ATTR_BINARY_SENSOR_WAN_STATE] = False

    async def _async_prepare_led(self, data: dict) -> None:
        """Prepare led.

        :param data: dict
        """

        response: dict = await self.luci.led()

        if "status" in response:
            data[ATTR_LIGHT_LED] = response["status"] == 1
        else:
            data[ATTR_LIGHT_LED] = False

    async def _async_prepare_wifi(self, data: dict) -> None:
        """Prepare wifi.

        :param data: dict
        """

        response: dict = await self.luci.wifi_detail_all()

        if "bsd" in response:
            data[ATTR_BINARY_SENSOR_DUAL_BAND] = response["bsd"] == 1
        else:
            data[ATTR_BINARY_SENSOR_DUAL_BAND] = False

        if "info" not in response:
            return

        length: int = 0

        for wifi in response["info"]:
            # Support only 5G , 2.4G and 5G Game
            if "ifname" not in wifi or wifi["ifname"] not in ["wl0", "wl1", "wl2"]:
                continue

            if "status" in wifi:
                length += 1
                data[IfName(wifi["ifname"]).phrase] = int(wifi["status"]) > 0

        data[ATTR_WIFI_ADAPTER_LENGTH] = length

    async def _async_prepare_devices(self, data: dict) -> None:
        """Prepare devices.

        :param data: dict
        """

        self.reset_counter()

        response: dict = await self.luci.wifi_connect_devices()

        if "list" in response:
            integrations: dict[str, dict] = {}

            if self.is_repeater and self.is_force_load:
                integrations = self.get_integrations()

            for device in response["list"]:
                self._signals[device["mac"]] = (
                    device["signal"] if "signal" in device else 0
                )

                if self.is_repeater and self.is_force_load:
                    device[ATTR_TRACKER_ENTRY_ID] = device[
                        ATTR_TRACKER_UPDATER_ENTRY_ID
                    ] = integrations[self.ip][ATTR_TRACKER_ENTRY_ID]

                    action: DeviceAction = DeviceAction.ADD
                    if self._mass_update_device(device, integrations):
                        action = DeviceAction.SKIP

                    self.add_device(device, action=action)

    async def _async_prepare_device_list(self, data: dict) -> None:
        """Prepare device list

        :param data: dict
        """

        if self.is_repeater:
            return

        response: dict = await self.luci.device_list()

        if "list" not in response or len(response["list"]) == 0:
            if len(self._signals) > 0 and not self.is_repeater:
                data[ATTR_SENSOR_MODE] = Mode.MESH

            return

        integrations: dict[str, dict] = self.get_integrations()

        mac_to_ip: dict[str, str] = {
            device["mac"]: device["ip"][0]["ip"]
            for device in response["list"]
            if "ip" in device and len(device["ip"]) > 0
        }

        add_to: dict = {}

        for device in response["list"]:
            action: DeviceAction = DeviceAction.ADD

            if (
                "parent" in device
                and len(device["parent"]) > 0
                and device["parent"] in mac_to_ip
                and mac_to_ip[device["parent"]] in integrations
                and mac_to_ip[device["parent"]] != self.ip
            ):
                integration: dict = integrations[mac_to_ip[device["parent"]]]

                if integration[UPDATER].is_force_load:
                    continue

                if device[ATTR_TRACKER_MAC] not in integration[UPDATER].devices:
                    action = DeviceAction.MOVE
                else:
                    action = DeviceAction.SKIP

                device[ATTR_TRACKER_ENTRY_ID] = integration[ATTR_TRACKER_ENTRY_ID]

                if ATTR_DEVICE_MAC_ADDRESS in integration[UPDATER].data:
                    if mac_to_ip[device["parent"]] not in add_to:
                        add_to[mac_to_ip[device["parent"]]] = []

                    add_to[mac_to_ip[device["parent"]]].append((device, action))
            else:
                device[ATTR_TRACKER_ENTRY_ID] = integrations[self.ip][
                    ATTR_TRACKER_ENTRY_ID
                ]

                if device[ATTR_TRACKER_MAC] in self._moved_devices:
                    if self._mass_update_device(device, integrations):
                        action = DeviceAction.SKIP

                    self._moved_devices.remove(device[ATTR_TRACKER_MAC])

            if device[ATTR_TRACKER_MAC] not in self._moved_devices:
                device[ATTR_TRACKER_UPDATER_ENTRY_ID] = integrations[self.ip][
                    ATTR_TRACKER_ENTRY_ID
                ]

                self.add_device(device, action=action)

        if len(add_to) == 0:
            return

        for ip, devices in add_to.items():
            if ip not in integrations:
                continue

            integrations[ip][UPDATER].reset_counter(True)
            for device in devices:
                integrations[ip][UPDATER].add_device(device[0], True, device[1])

    def add_device(
        self,
        device: dict,
        is_from_parent: bool = False,
        action: DeviceAction = DeviceAction.ADD,
    ) -> None:
        """Prepare device.

        :param device: dict
        :param is_from_parent: bool: The call came from a third party integration
        :param action: DeviceAction: Device action
        """

        if ATTR_TRACKER_MAC not in device or (is_from_parent and self.is_force_load):
            return

        is_new: bool = device[ATTR_TRACKER_MAC] not in self.devices

        ip_attr: dict | None = device["ip"][0] if "ip" in device else None
        connection: Connection | None = (
            Connection(int(device["type"])) if "type" in device else None
        )

        self.devices[device[ATTR_TRACKER_MAC]] = {
            ATTR_TRACKER_ENTRY_ID: device[ATTR_TRACKER_ENTRY_ID],
            ATTR_TRACKER_UPDATER_ENTRY_ID: device.get(
                ATTR_TRACKER_UPDATER_ENTRY_ID, device[ATTR_TRACKER_ENTRY_ID]
            ),
            ATTR_TRACKER_MAC: device[ATTR_TRACKER_MAC],
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: self.data.get(
                ATTR_DEVICE_MAC_ADDRESS, None
            ),
            ATTR_TRACKER_SIGNAL: self._signals[device[ATTR_TRACKER_MAC]]
            if device[ATTR_TRACKER_MAC] in self._signals
            else None,
            ATTR_TRACKER_NAME: device["name"]
            if "name" in device
            else device[ATTR_TRACKER_MAC],
            ATTR_TRACKER_IP: ip_attr["ip"] if ip_attr is not None else None,
            ATTR_TRACKER_CONNECTION: connection,
            ATTR_TRACKER_DOWN_SPEED: float(ip_attr["downspeed"])
            if ip_attr is not None
            and "downspeed" in ip_attr
            and float(ip_attr["downspeed"]) > 0
            else 0.0,
            ATTR_TRACKER_UP_SPEED: float(ip_attr["upspeed"])
            if ip_attr is not None
            and "upspeed" in ip_attr
            and float(ip_attr["upspeed"]) > 0
            else 0.0,
            ATTR_TRACKER_ONLINE: str(
                timedelta(seconds=int(ip_attr["online"] if ip_attr is not None else 0))
            ),
            ATTR_TRACKER_LAST_ACTIVITY: datetime.now()
            .replace(microsecond=0)
            .isoformat(),
        }

        if not is_from_parent and action == DeviceAction.MOVE:
            self._moved_devices.append(device[ATTR_TRACKER_MAC])

            action = DeviceAction.ADD

        if (
            is_new
            and action == DeviceAction.ADD
            and self.new_device_callback is not None
        ):
            async_dispatcher_send(
                self.hass, SIGNAL_NEW_DEVICE, self.devices[device[ATTR_TRACKER_MAC]]
            )

            _LOGGER.debug(
                "Found new device: %s", self.devices[device[ATTR_TRACKER_MAC]]
            )
        elif action == DeviceAction.MOVE:
            _LOGGER.debug("Move device: %s", device[ATTR_TRACKER_MAC])

        if ATTR_SENSOR_DEVICES not in self.data:
            self.data[ATTR_SENSOR_DEVICES] = 1
        else:
            self.data[ATTR_SENSOR_DEVICES] += 1

        if connection is None:
            return

        code: str = connection.name.replace("WIFI_", "")
        code = f"{ATTR_SENSOR_DEVICES}_{code}".lower()

        if code not in self.data:
            self.data[code] = 1
        else:
            self.data[code] += 1

    def _mass_update_device(self, device: dict, integrations: dict | None = None) -> bool:
        """Mass update devices

        :param device: Device data
        :param integrations | None: Integration list
        :return bool: is found
        """

        if integrations is None:
            integrations = self.get_integrations()

        is_found: bool = False

        for integration in integrations.values():
            if device[ATTR_TRACKER_MAC] not in integration[UPDATER].devices:
                continue

            integration[UPDATER].devices[device[ATTR_TRACKER_MAC]] = device
            is_found = True

        return is_found

    async def _async_prepare_new_status(self, data: dict) -> None:
        """Prepare new status.

        :param data: dict
        """

        if not self.is_force_load:
            return

        response: dict = await self.luci.new_status()

        if "2g" in response:
            data[ATTR_SENSOR_DEVICES_2_4] = response["2g"]["online_sta_count"]

        if "5g" in response:
            data[ATTR_SENSOR_DEVICES_5_0] = response["5g"]["online_sta_count"]

        if "game" in response:
            data[ATTR_SENSOR_DEVICES_5_0] = response["game"]["online_sta_count"]

    def _clean_devices(self) -> None:
        """Clean devices."""

        if self._activity_days == 0 or len(self.devices) == 0:
            return

        now = datetime.now().replace(microsecond=0)
        integrations: dict = self.get_integrations()
        devices: dict = self.devices

        for mac, device in devices.items():
            delta = now - datetime.strptime(
                device[ATTR_TRACKER_LAST_ACTIVITY], "%Y-%m-%dT%H:%M:%S"
            )

            if int(delta.days) <= self._activity_days:
                continue

            for ip, integration in integrations.items():
                if (
                    ip != self.ip
                    and not integration[UPDATER].is_force_load
                    and mac in integration[UPDATER].devices
                ):
                    del integration[UPDATER].devices[mac]

            del self.devices[mac]

    def get_integrations(self) -> dict[str, dict]:
        """Mapping integration for device tracker

        :return dict[str, dict]: Mapping
        """

        return {
            integration[CONF_IP_ADDRESS]: {
                UPDATER: integration[UPDATER],
                ATTR_TRACKER_ENTRY_ID: entry_id,
            }
            for entry_id, integration in self.hass.data[DOMAIN].items()
            if isinstance(integration, dict)
        }

    def reset_counter(self, is_force: bool = False) -> None:
        """Reset counter

        :param is_force: bool: Force reset
        """

        if self.is_repeater and not self.is_force_load and not is_force:
            return

        self.data[ATTR_SENSOR_DEVICES] = 0
        self.data[ATTR_SENSOR_DEVICES_LAN] = 0
        self.data[ATTR_SENSOR_DEVICES_GUEST] = 0
        self.data[ATTR_SENSOR_DEVICES_2_4] = 0
        self.data[ATTR_SENSOR_DEVICES_5_0] = 0
        self.data[ATTR_SENSOR_DEVICES_5_0_GAME] = 0

    async def _async_load_devices(self) -> None:
        """Async load devices from Store"""

        if self._store is None:
            return

        devices: dict | None = await self._store.async_load()

        if devices is None or not isinstance(devices, dict) or len(devices) == 0:
            return

        for mac, data in devices.items():
            if mac in self.devices:
                continue

            self.devices[mac] = data

        self._clean_devices()

    async def _async_save_devices(self) -> None:
        """Async save devices to Store"""

        if self._store is None or (self.is_repeater and not self.is_force_load):
            return

        await self._store.async_save(self.devices)

    async def _async_load_manufacturers(self) -> None:
        """Async load _manufacturers"""

        self._manufacturers = await self.hass.async_add_executor_job(
            json.load_json,
            f"{os.path.dirname(os.path.abspath(__file__))}/_manufacturers.json",
        )

    def manufacturer(self, mac: str | None) -> str | None:
        """Get manufacturer by mac address

        :param mac: str | None: Mac address
        :return str | None: Manufacturer
        """

        if mac is None:
            return None

        identifier: str = mac.replace(":", "").upper()[0:6]

        return (
            self._manufacturers[identifier]
            if identifier in self._manufacturers
            else None
        )
