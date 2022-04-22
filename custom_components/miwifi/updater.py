"""Luci data updater."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from functools import cached_property
from typing import Final, Any

from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant, CALLBACK_TYPE
import homeassistant.components.persistent_notification as pn
from homeassistant.helpers import event
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import json, utcnow
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
    ATTR_MODEL,
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
    ATTR_SENSOR_AP_SIGNAL,
    ATTR_SENSOR_WAN_DOWNLOAD_SPEED,
    ATTR_SENSOR_WAN_UPLOAD_SPEED,
    ATTR_SENSOR_DEVICES,
    ATTR_SENSOR_DEVICES_LAN,
    ATTR_SENSOR_DEVICES_GUEST,
    ATTR_SENSOR_DEVICES_2_4,
    ATTR_SENSOR_DEVICES_5_0,
    ATTR_SENSOR_DEVICES_5_0_GAME,
    ATTR_CAMERA_IMAGE,
    ATTR_LIGHT_LED,
    ATTR_WIFI_DATA_FIELDS,
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
    ATTR_TRACKER_OPTIONAL_MAC,
    ATTR_UPDATE_FIRMWARE,
    ATTR_UPDATE_TITLE,
    ATTR_UPDATE_CURRENT_VERSION,
    ATTR_UPDATE_LATEST_VERSION,
    ATTR_UPDATE_RELEASE_URL,
    ATTR_UPDATE_DOWNLOAD_URL,
    ATTR_UPDATE_FILE_SIZE,
    ATTR_UPDATE_FILE_HASH,
)
from .enum import (
    Model,
    Mode,
    Connection,
    IfName,
    Wifi,
    DeviceAction,
)
from .exceptions import LuciConnectionException, LuciTokenException, LuciException
from .luci import LuciClient
from .self_check import async_self_check

PREPARE_METHODS: Final = [
    "init",
    "status",
    "rom_update",
    "mode",
    "wan",
    "led",
    "wifi",
    "channels",
    "devices",
    "device_list",
    "device_restore",
    "ap",
    "new_status",
]

UNSUPPORTED: Final = {
    "new_status": [
        Model.R1D,
        Model.R2D,
        Model.R1CM,
        Model.R1CL,
        Model.R3P,
        Model.R3D,
        Model.R3L,
        Model.R3A,
        Model.R3,
        Model.R3G,
        Model.R4,
        Model.R4A,
        Model.R4AC,
        Model.R4C,
        Model.R4CM,
        Model.D01,
    ]
}

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-branches,too-many-lines,too-many-arguments
class LuciUpdater(DataUpdateCoordinator):
    """Luci data updater for interaction with Luci API."""

    luci: LuciClient
    code: codes = codes.BAD_GATEWAY
    ip: str
    new_device_callback: CALLBACK_TYPE | None = None
    is_force_load: bool = False

    _manufacturers: dict[str, str] = {}

    _store: Store | None = None

    _entry_id: str | None = None
    _scan_interval: int
    _activity_days: int
    _is_only_login: bool = False
    _is_reauthorization: bool = True
    _is_first_update: bool = True

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
        entry_id: str | None = None,
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
        :param entry_id: str | None: Entry ID
        """

        self.luci = LuciClient(get_async_client(hass, False), ip, password, timeout)

        self.ip = ip  # pylint: disable=invalid-name
        self.is_force_load = is_force_load

        self._store = store

        self._entry_id = entry_id

        self._scan_interval = scan_interval
        self._activity_days = activity_days
        self._is_only_login = is_only_login

        if hass is not None:
            super().__init__(
                hass,
                _LOGGER,
                name="MiWifi updater",
                update_interval=self._update_interval,
                update_method=self.update,
            )

        self.data: dict[str, Any] = {}
        self.devices: dict[str, dict[str, Any]] = {}

    async def async_stop(self) -> None:
        """Stop updater"""

        if self.new_device_callback is not None:
            self.new_device_callback()  # pylint: disable=not-callable

        await self._async_save_devices()
        await self.luci.logout()

    @cached_property
    def _update_interval(self) -> timedelta:
        """Update interval

        :return timedelta: update_interval
        """

        return timedelta(seconds=self._scan_interval)

    async def update(self, retry: int = 1) -> dict:
        """Update miwifi information.

        :param retry: int: Retry count
        :return dict: dict with luci data.
        """

        await self._async_load_manufacturers()

        _is_before_reauthorization: bool = self._is_reauthorization
        _err: LuciException | None = None

        try:
            if self._is_reauthorization or self._is_only_login or self._is_first_update:
                if self._is_first_update:
                    await self.luci.logout()
                    await asyncio.sleep(DEFAULT_CALL_DELAY)

                await self.luci.login()

            for method in PREPARE_METHODS:
                if not self._is_only_login or method == "init":
                    await self._async_prepare(method, self.data)
        except LuciConnectionException as _e:
            _err = _e

            self._is_reauthorization = False
            self.code = codes.NOT_FOUND
        except LuciTokenException as _e:
            _err = _e

            self._is_reauthorization = True
            self.code = codes.FORBIDDEN
        else:
            self.code = codes.OK

            self._is_reauthorization = False

            if self._is_first_update:
                self._is_first_update = False

        self.data[ATTR_STATE] = codes.is_success(self.code)

        if (
            not self._is_first_update
            and not _is_before_reauthorization
            and self._is_reauthorization
        ):
            self.data[ATTR_STATE] = True

        if self._is_first_update and not self.data[ATTR_STATE]:
            if retry > DEFAULT_RETRY and _err is not None:
                raise _err

            if retry <= DEFAULT_RETRY:
                _LOGGER.warning(
                    "Error connecting to router (attempt #%s of %s): %r",
                    retry,
                    DEFAULT_RETRY,
                    _err,
                )

                await asyncio.sleep(retry)

                return await self.update(retry + 1)

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

        if self._unsub_refresh:  # type: ignore
            self._unsub_refresh()  # type: ignore
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

        if (
            method in UNSUPPORTED
            and data.get(ATTR_MODEL, Model.NOT_KNOWN) in UNSUPPORTED[method]
        ):
            return

        action = getattr(self, f"_async_prepare_{method}")

        if action:
            await action(data)

    async def _async_prepare_init(self, data: dict) -> None:
        """Prepare init info.

        :param data: dict
        """

        if not self._is_first_update:
            return

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

        if "hardware" in response:
            try:
                data[ATTR_MODEL] = Model(response["hardware"].lower())
            except ValueError as _e:
                await async_self_check(self.hass, self.luci, response["hardware"])

                if not self._is_only_login:
                    raise LuciException(f"Router {self.ip} not supported") from _e

                self.code = codes.CONFLICT

            data[ATTR_CAMERA_IMAGE] = await self.luci.image(response["hardware"])

            return

        pn.async_create(self.hass, f"Router {self.ip} not supported", "MiWifi")

        if not self._is_only_login:
            raise LuciException(f"Router {self.ip} not supported")

        self.code = codes.CONFLICT

    async def _async_prepare_status(self, data: dict) -> None:
        """Prepare status.

        :param data: dict
        """

        response: dict = await self.luci.status()

        if "hardware" in response and isinstance(response["hardware"], dict):
            if "mac" in response["hardware"]:
                data[ATTR_DEVICE_MAC_ADDRESS] = response["hardware"]["mac"]
            if "version" in response["hardware"]:
                data[ATTR_UPDATE_CURRENT_VERSION] = response["hardware"]["version"]

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

        if "wan" in response and isinstance(response["wan"], dict):
            # fmt: off
            data[ATTR_SENSOR_WAN_DOWNLOAD_SPEED] = float(
                response["wan"]["downspeed"]
            ) if "downspeed" in response["wan"] else 0

            data[ATTR_SENSOR_WAN_UPLOAD_SPEED] = float(
                response["wan"]["upspeed"]
            ) if "upspeed" in response["wan"] else 0
            # fmt: on

    async def _async_prepare_rom_update(self, data: dict) -> None:
        """Prepare rom update.

        :param data: dict
        """

        if ATTR_UPDATE_CURRENT_VERSION not in data:
            return

        response: dict = await self.luci.rom_update()

        _rom_info: dict = {
            ATTR_UPDATE_CURRENT_VERSION: data[ATTR_UPDATE_CURRENT_VERSION],
            ATTR_UPDATE_LATEST_VERSION: data[ATTR_UPDATE_CURRENT_VERSION],
            ATTR_UPDATE_TITLE: f"{data.get(ATTR_DEVICE_MANUFACTURER, DEFAULT_MANUFACTURER)}"
            + f" {data.get(ATTR_MODEL, Model.NOT_KNOWN).name}"
            + f" ({data.get(ATTR_DEVICE_NAME, DEFAULT_NAME)})",
        }

        if "needUpdate" not in response or response["needUpdate"] != 1:
            data[ATTR_UPDATE_FIRMWARE] = _rom_info

            return

        try:
            data[ATTR_UPDATE_FIRMWARE] = _rom_info | {
                ATTR_UPDATE_LATEST_VERSION: response["version"],
                ATTR_UPDATE_DOWNLOAD_URL: response["downloadUrl"],
                ATTR_UPDATE_RELEASE_URL: response["changelogUrl"],
                ATTR_UPDATE_FILE_SIZE: response["fileSize"],
                ATTR_UPDATE_FILE_HASH: response["fullHash"],
            }
        except KeyError:
            pass

    async def _async_prepare_mode(self, data: dict) -> None:
        """Prepare mode.

        :param data: dict
        """

        if data.get(ATTR_SENSOR_MODE, Mode.DEFAULT) == Mode.MESH:
            return

        response: dict = await self.luci.mode()

        if "mode" in response:
            try:
                data[ATTR_SENSOR_MODE] = Mode(int(response["mode"]))
            except ValueError:
                pass

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

        # Support only 5G , 2.4G,  5G Game and Guest
        for wifi in response["info"]:
            if "ifname" not in wifi:
                continue

            try:
                adapter: IfName = IfName(wifi["ifname"])
            except ValueError:
                continue

            if "status" in wifi:
                data[adapter.phrase] = int(wifi["status"]) > 0  # type: ignore

                # Guest network is not an adapter
                if adapter != IfName.WL14:
                    length += 1

            if "channelInfo" in wifi and "channel" in wifi["channelInfo"]:
                data[f"{adapter.phrase}_channel"] = str(  # type: ignore
                    wifi["channelInfo"]["channel"]
                )

            if "txpwr" in wifi:
                data[f"{adapter.phrase}_signal_strength"] = wifi["txpwr"]  # type: ignore

            wifi_data: dict = {}

            for data_field, field in ATTR_WIFI_DATA_FIELDS.items():
                if "channelInfo" in data_field and "channelInfo" in wifi:
                    data_field = data_field.replace("channelInfo", "")

                    if data_field in wifi["channelInfo"]:
                        wifi_data[field] = wifi["channelInfo"][data_field]
                elif data_field in wifi:
                    wifi_data[field] = wifi[data_field]

            if len(wifi_data) > 0:
                data[f"{adapter.phrase}_data"] = wifi_data  # type: ignore

        data[ATTR_WIFI_ADAPTER_LENGTH] = length

    async def _async_prepare_channels(self, data: dict) -> None:
        """Prepare channels.

        :param data: dict
        """

        if not self._is_first_update or ATTR_WIFI_ADAPTER_LENGTH not in data:
            return

        for index in range(1, data.get(ATTR_WIFI_ADAPTER_LENGTH, 2) + 1):
            response: dict = await self.luci.avaliable_channels(index)

            if "list" not in response or len(response["list"]) == 0:
                continue

            try:
                data[Wifi(index).phrase + "_channels"] = [  # type: ignore
                    str(channel["c"])
                    for channel in response["list"]
                    if "c" in channel and int(channel["c"]) > 0
                ]
            except ValueError:
                pass

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
                # fmt: off
                self._signals[device["mac"]] = device["signal"] \
                    if "signal" in device else 0
                # fmt: on

                if device["mac"] in self.devices:
                    # fmt: off
                    self.devices[device["mac"]][ATTR_TRACKER_LAST_ACTIVITY] = datetime.now() \
                        .replace(microsecond=0) \
                        .isoformat()
                    # fmt: on

                if self.is_repeater and self.is_force_load:
                    device |= {
                        ATTR_TRACKER_ENTRY_ID: self._entry_id,
                        ATTR_TRACKER_UPDATER_ENTRY_ID: self._entry_id,
                    }

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
                        add_to[mac_to_ip[device["parent"]]] = {}

                    add_to[mac_to_ip[device["parent"]]][device[ATTR_TRACKER_MAC]] = (
                        device,
                        action,
                    )
            else:
                device[ATTR_TRACKER_ENTRY_ID] = self._entry_id

                if device[ATTR_TRACKER_MAC] in self._moved_devices:
                    if self._mass_update_device(device, integrations):
                        action = DeviceAction.SKIP

                    self._moved_devices.remove(device[ATTR_TRACKER_MAC])

            if device[ATTR_TRACKER_MAC] not in self._moved_devices:
                device[ATTR_TRACKER_UPDATER_ENTRY_ID] = self._entry_id

                self.add_device(device, action=action, integrations=integrations)

        if len(add_to) == 0:
            return

        await asyncio.sleep(DEFAULT_CALL_DELAY)

        for _ip, devices in add_to.items():
            if _ip not in integrations:
                continue

            integrations[_ip][UPDATER].reset_counter(True)
            for device in devices.values():
                integrations[_ip][UPDATER].add_device(
                    device[0], True, device[1], integrations
                )

    async def _async_prepare_device_restore(self, data: dict) -> None:
        """Restore devices

        :param data: dict
        """

        if not self._is_first_update:
            return

        devices: dict | None = await self._async_load_devices()

        if devices is None:
            return

        integrations: dict = self.get_integrations()

        for mac, device in devices.items():
            if mac in self.devices:
                continue

            if device[ATTR_TRACKER_ENTRY_ID] != self._entry_id:
                for integration in integrations.values():
                    if (
                        not integration[UPDATER].is_force_load
                        and integration[ATTR_TRACKER_ENTRY_ID]
                        == device[ATTR_TRACKER_ENTRY_ID]
                        and mac not in integration[UPDATER].devices
                    ):
                        device[ATTR_TRACKER_ROUTER_MAC_ADDRESS] = integration[
                            UPDATER
                        ].data.get(
                            ATTR_DEVICE_MAC_ADDRESS,
                            device[ATTR_TRACKER_ROUTER_MAC_ADDRESS],
                        )

                        integration[UPDATER].devices[mac] = device

                        self._moved_devices.append(mac)

                        break

            self.devices[mac] = device

            async_dispatcher_send(self.hass, SIGNAL_NEW_DEVICE, device)

            _LOGGER.debug("Restore device: %s, %s", mac, device)

        self._clean_devices()

    def add_device(
        self,
        device: dict,
        is_from_parent: bool = False,
        action: DeviceAction = DeviceAction.ADD,
        integrations: dict[str, Any] | None = None,
    ) -> None:
        """Prepare device.

        :param device: dict
        :param is_from_parent: bool: The call came from a third party integration
        :param action: DeviceAction: Device action
        :param integrations: dict[str, Any]: Integrations list
        """

        if ATTR_TRACKER_MAC not in device or (is_from_parent and self.is_force_load):
            return

        is_new: bool = device[ATTR_TRACKER_MAC] not in self.devices

        ip_attr: dict | None = device["ip"][0] if "ip" in device else None

        if self.is_force_load and "wifiIndex" in device:
            device["type"] = 6 if device["wifiIndex"] == 3 else device["wifiIndex"]

        connection: Connection | None = None

        try:
            # fmt: off
            connection = Connection(int(device["type"])) \
                if "type" in device else None
            # fmt: on
        except ValueError:
            pass

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
            ATTR_TRACKER_OPTIONAL_MAC: integrations[ip_attr["ip"]][UPDATER].data.get(
                ATTR_DEVICE_MAC_ADDRESS, None
            )
            if integrations is not None
            and ip_attr is not None
            and ip_attr["ip"] in integrations
            else None,
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

    def _mass_update_device(
        self, device: dict, integrations: dict | None = None
    ) -> bool:
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

    async def _async_prepare_ap(self, data: dict) -> None:
        """Prepare wifi ap.

        :param data: dict
        """

        if self.data.get(ATTR_SENSOR_MODE, Mode.DEFAULT) not in [
            Mode.ACCESS_POINT,
            Mode.REPEATER,
        ]:
            return

        response: dict = await self.luci.wifi_ap_signal()

        if "signal" in response and isinstance(response["signal"], int):
            data[ATTR_SENSOR_AP_SIGNAL] = response["signal"]

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
            if ATTR_TRACKER_LAST_ACTIVITY not in device or not isinstance(
                device[ATTR_TRACKER_LAST_ACTIVITY], str
            ):
                # fmt: off
                self.devices[mac][ATTR_TRACKER_LAST_ACTIVITY] = \
                    datetime.now().replace(microsecond=0).isoformat()
                # fmt: on

                continue

            delta = now - datetime.strptime(
                device[ATTR_TRACKER_LAST_ACTIVITY], "%Y-%m-%dT%H:%M:%S"
            )

            if int(delta.days) <= self._activity_days:
                continue

            for _ip, integration in integrations.items():
                if (
                    _ip != self.ip
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

    async def _async_load_devices(self) -> dict | None:
        """Async load devices from Store"""

        if self._store is None:
            return None

        devices: dict | None = await self._store.async_load()

        if devices is None or not isinstance(devices, dict) or len(devices) == 0:
            return None

        return devices

    async def _async_save_devices(self) -> None:
        """Async save devices to Store"""

        if (
            self._store is None
            or (self.is_repeater and not self.is_force_load)
            or len(self.devices) == 0
        ):
            return

        await self._store.async_save(self.devices)

    async def _async_load_manufacturers(self) -> None:
        """Async load _manufacturers"""

        if len(self._manufacturers) > 0:
            return

        self._manufacturers = await self.hass.async_add_executor_job(
            json.load_json,
            f"{os.path.dirname(os.path.abspath(__file__))}/manufacturers.json",
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
