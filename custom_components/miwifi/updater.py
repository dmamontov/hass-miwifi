"""Luci data updater."""


from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta
from functools import cached_property
from typing import Any, Final

import homeassistant.components.persistent_notification as pn
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import event
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import utcnow
from httpx import codes

from .const import (
    ATTR_BINARY_SENSOR_DUAL_BAND,
    ATTR_BINARY_SENSOR_VPN_STATE,
    ATTR_BINARY_SENSOR_WAN_STATE,
    ATTR_DEVICE_HW_VERSION,
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_DEVICE_MANUFACTURER,
    ATTR_DEVICE_MODEL,
    ATTR_DEVICE_NAME,
    ATTR_DEVICE_SW_VERSION,
    ATTR_LIGHT_LED,
    ATTR_MODEL,
    ATTR_SENSOR_AP_SIGNAL,
    ATTR_SENSOR_DEVICES,
    ATTR_SENSOR_DEVICES_2_4,
    ATTR_SENSOR_DEVICES_5_0,
    ATTR_SENSOR_DEVICES_5_0_GAME,
    ATTR_SENSOR_DEVICES_GUEST,
    ATTR_SENSOR_DEVICES_LAN,
    ATTR_SENSOR_MEMORY_TOTAL,
    ATTR_SENSOR_MEMORY_USAGE,
    ATTR_SENSOR_MODE,
    ATTR_SENSOR_TEMPERATURE,
    ATTR_SENSOR_UPTIME,
    ATTR_SENSOR_VPN_UPTIME,
    ATTR_SENSOR_WAN_DOWNLOAD_SPEED,
    ATTR_SENSOR_WAN_UPLOAD_SPEED,
    ATTR_STATE,
    ATTR_SWITCH_WIFI_5_0_GAME,
    ATTR_TRACKER_CONNECTION,
    ATTR_TRACKER_DOWN_SPEED,
    ATTR_TRACKER_ENTRY_ID,
    ATTR_TRACKER_IP,
    ATTR_TRACKER_IS_RESTORED,
    ATTR_TRACKER_LAST_ACTIVITY,
    ATTR_TRACKER_MAC,
    ATTR_TRACKER_NAME,
    ATTR_TRACKER_ONLINE,
    ATTR_TRACKER_OPTIONAL_MAC,
    ATTR_TRACKER_ROUTER_MAC_ADDRESS,
    ATTR_TRACKER_SIGNAL,
    ATTR_TRACKER_UP_SPEED,
    ATTR_TRACKER_UPDATER_ENTRY_ID,
    ATTR_UPDATE_CURRENT_VERSION,
    ATTR_UPDATE_DOWNLOAD_URL,
    ATTR_UPDATE_FILE_HASH,
    ATTR_UPDATE_FILE_SIZE,
    ATTR_UPDATE_FIRMWARE,
    ATTR_UPDATE_LATEST_VERSION,
    ATTR_UPDATE_RELEASE_URL,
    ATTR_UPDATE_TITLE,
    ATTR_WIFI_ADAPTER_LENGTH,
    ATTR_WIFI_DATA_FIELDS,
    DEFAULT_ACTIVITY_DAYS,
    DEFAULT_CALL_DELAY,
    DEFAULT_MANUFACTURER,
    DEFAULT_NAME,
    DEFAULT_RETRY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    NAME,
    SIGNAL_NEW_DEVICE,
    UPDATER,
)
from .enum import (
    Connection,
    DeviceAction,
    EncryptionAlgorithm,
    IfName,
    Mode,
    Model,
    Wifi,
)
from .exceptions import LuciConnectionError, LuciError, LuciRequestError
from .luci import LuciClient
from .self_check import async_self_check

PREPARE_METHODS: Final = (
    "init",
    "status",
    "vpn",
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
)

NEW_STATUS_MAP: Final = {
    "2g": ATTR_SENSOR_DEVICES_2_4,
    "5g": ATTR_SENSOR_DEVICES_5_0,
    "game": ATTR_SENSOR_DEVICES_5_0_GAME,
}

REPEATER_SKIP_ATTRS: Final = (
    ATTR_TRACKER_NAME,
    ATTR_TRACKER_IP,
    ATTR_TRACKER_DOWN_SPEED,
    ATTR_TRACKER_UP_SPEED,
    ATTR_TRACKER_ONLINE,
    ATTR_TRACKER_OPTIONAL_MAC,
)

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
    supports_guest: bool = True

    _store: Store | None = None

    _entry_id: str | None = None
    _scan_interval: int
    _activity_days: int
    _is_only_login: bool = False
    _is_reauthorization: bool = True

    def __init__(
        self,
        hass: HomeAssistant,
        ip: str,
        password: str,
        encryption: str = EncryptionAlgorithm.SHA1,
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
        :param encryption: str: password encryption algorithm
        :param scan_interval: int: Update interval
        :param timeout: int: Query execution timeout
        :param is_force_load: bool: Force boot devices when using repeater and mesh mode
        :param activity_days: int: Allowed number of days to wait after the last activity
        :param store: Store | None: Device store
        :param is_only_login: bool: Only config flow
        :param entry_id: str | None: Entry ID
        """

        self.luci = LuciClient(
            get_async_client(hass, False),
            ip,
            password,
            EncryptionAlgorithm(encryption),
            timeout,
        )

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
                name=f"{NAME} updater",
                update_interval=self._update_interval,
                update_method=self.update,
            )

        self.data: dict[str, Any] = {}
        self.devices: dict[str, dict[str, Any]] = {}
        self._signals: dict[str, int] = {}
        self._moved_devices: list = []
        self._is_first_update: bool = True

    async def async_stop(self, clean_store: bool = False) -> None:
        """Stop updater

        :param clean_store: bool
        """

        if self.new_device_callback is not None:
            self.new_device_callback()  # pylint: disable=not-callable

        if clean_store and self._store is not None:
            await self._store.async_remove()
        else:
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

        self.code = codes.OK

        _is_before_reauthorization: bool = self._is_reauthorization
        _err: LuciError | None = None

        try:
            if self._is_reauthorization or self._is_only_login or self._is_first_update:
                if self._is_first_update and retry == 1:
                    await self.luci.logout()
                    await asyncio.sleep(DEFAULT_CALL_DELAY)

                await self.luci.login()

            for method in PREPARE_METHODS:
                if not self._is_only_login or method == "init":
                    await self._async_prepare(method, self.data)
        except LuciConnectionError as _e:
            _err = _e

            self._is_reauthorization = False
            self.code = codes.NOT_FOUND
        except LuciRequestError as _e:
            _err = _e

            self._is_reauthorization = True
            self.code = codes.FORBIDDEN
        else:
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

        if (
            not self._is_only_login
            and self._is_first_update
            and not self.data[ATTR_STATE]
        ):
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
    def supports_wan(self) -> bool:
        """Is supports wan

        :return bool
        """

        return self.data.get(ATTR_BINARY_SENSOR_WAN_STATE, False)

    @property
    def supports_game(self) -> bool:
        """Is supports game mode

        :return bool
        """

        return self.data.get(ATTR_SWITCH_WIFI_5_0_GAME, None) is not None

    @property
    def supports_update(self) -> bool:
        """Is supports update

        :return bool
        """

        return len(self.data.get(ATTR_UPDATE_FIRMWARE, {})) != 0

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
                ),
                (CONF_IP_ADDRESS, self.ip),
            },
            name=self.data.get(ATTR_DEVICE_NAME, DEFAULT_NAME),
            manufacturer=self.data.get(ATTR_DEVICE_MANUFACTURER, DEFAULT_MANUFACTURER),
            model=self.data.get(ATTR_DEVICE_MODEL, None),
            sw_version=self.data.get(ATTR_DEVICE_SW_VERSION, None),
            hw_version=self.data.get(ATTR_DEVICE_HW_VERSION, None),
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

        if action := getattr(self, f"_async_prepare_{method}"):
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
                    raise LuciError(f"Router {self.ip} not supported") from _e

                self.code = codes.CONFLICT

            return

        pn.async_create(self.hass, f"Router {self.ip} not supported", NAME)

        if not self._is_only_login:
            raise LuciError(f"Router {self.ip} not supported")

        self.code = codes.CONFLICT

    async def _async_prepare_status(self, data: dict) -> None:
        """Prepare status.

        :param data: dict
        """

        response: dict = await self.luci.status()

        if "hardware" in response and isinstance(response["hardware"], dict):
            if "mac" in response["hardware"]:
                data[ATTR_DEVICE_MAC_ADDRESS] = response["hardware"]["mac"]
            if "sn" in response["hardware"]:
                data[ATTR_DEVICE_HW_VERSION] = response["hardware"]["sn"]
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

    async def _async_prepare_vpn(self, data: dict) -> None:
        """Prepare vpn.

        :param data: dict
        """

        with contextlib.suppress(LuciError):
            response: dict = await self.luci.vpn_status()

            data |= {
                ATTR_SENSOR_VPN_UPTIME: 0,
                ATTR_BINARY_SENSOR_VPN_STATE: False,
            }

            if "uptime" in response:
                data |= {
                    ATTR_SENSOR_VPN_UPTIME: str(
                        timedelta(seconds=int(float(response["uptime"])))
                    ),
                    ATTR_BINARY_SENSOR_VPN_STATE: int(float(response["uptime"])) > 0,
                }

    async def _async_prepare_rom_update(self, data: dict) -> None:
        """Prepare rom update.

        :param data: dict
        """

        if ATTR_UPDATE_CURRENT_VERSION not in data:
            return

        _rom_info: dict = {
            ATTR_UPDATE_CURRENT_VERSION: data[ATTR_UPDATE_CURRENT_VERSION],
            ATTR_UPDATE_LATEST_VERSION: data[ATTR_UPDATE_CURRENT_VERSION],
            ATTR_UPDATE_TITLE: f"{data.get(ATTR_DEVICE_MANUFACTURER, DEFAULT_MANUFACTURER)}"
            + f" {data.get(ATTR_MODEL, Model.NOT_KNOWN).name}"
            + f" ({data.get(ATTR_DEVICE_NAME, DEFAULT_NAME)})",
        }

        try:
            response: dict = await self.luci.rom_update()
        except LuciError:
            response = {}

        if (
            not isinstance(response, dict)
            or "needUpdate" not in response
            or response["needUpdate"] != 1
        ):
            data[ATTR_UPDATE_FIRMWARE] = _rom_info

            return

        with contextlib.suppress(KeyError):
            data[ATTR_UPDATE_FIRMWARE] = _rom_info | {
                ATTR_UPDATE_LATEST_VERSION: response["version"],
                ATTR_UPDATE_DOWNLOAD_URL: response["downloadUrl"],
                ATTR_UPDATE_RELEASE_URL: response["changelogUrl"],
                ATTR_UPDATE_FILE_SIZE: response["fileSize"],
                ATTR_UPDATE_FILE_HASH: response["fullHash"],
            }

    async def _async_prepare_mode(self, data: dict) -> None:
        """Prepare mode.

        :param data: dict
        """

        if data.get(ATTR_SENSOR_MODE, Mode.DEFAULT) == Mode.MESH:
            return

        response: dict = await self.luci.mode()

        if "mode" in response:
            with contextlib.suppress(ValueError):
                data[ATTR_SENSOR_MODE] = Mode(int(response["mode"]))

                return

        data[ATTR_SENSOR_MODE] = Mode.DEFAULT

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

            return

        data[ATTR_BINARY_SENSOR_WAN_STATE] = False

    async def _async_prepare_led(self, data: dict) -> None:
        """Prepare led.

        :param data: dict
        """

        response: dict = await self.luci.led()

        if "status" in response:
            data[ATTR_LIGHT_LED] = response["status"] == 1

            return

        data[ATTR_LIGHT_LED] = False

    async def _async_prepare_wifi(self, data: dict) -> None:
        """Prepare wifi.

        :param data: dict
        """

        try:
            response: dict = await self.luci.wifi_detail_all()
        except LuciError:
            return

        # fmt: off
        data[ATTR_BINARY_SENSOR_DUAL_BAND] = int(response["bsd"]) == 1 \
            if "bsd" in response else False
        # fmt: on

        if "info" not in response or len(response["info"]) == 0:
            return

        _adapters: list = await self._async_prepare_wifi_guest(response["info"])

        length: int = 0

        # Support only 5G , 2.4G, 5G Game and Guest
        for wifi in _adapters:
            if "ifname" not in wifi:
                continue

            try:
                adapter: IfName = IfName(wifi["ifname"])
            except ValueError:
                continue

            # Guest network is not an adapter
            if adapter != IfName.WL14:
                length += 1

            if "status" in wifi:
                data[adapter.phrase] = int(wifi["status"]) > 0  # type: ignore

            if "channelInfo" in wifi and "channel" in wifi["channelInfo"]:
                data[f"{adapter.phrase}_channel"] = str(  # type: ignore
                    wifi["channelInfo"]["channel"]
                )

            if "txpwr" in wifi:
                data[f"{adapter.phrase}_signal_strength"] = wifi["txpwr"]  # type: ignore

            if wifi_data := self._prepare_wifi_data(wifi):
                data[f"{adapter.phrase}_data"] = wifi_data  # type: ignore

        data[ATTR_WIFI_ADAPTER_LENGTH] = length

    async def _async_prepare_wifi_guest(self, adapters: list) -> list:
        """Prepare wifi guest.

        :param adapters: list
        :return list: adapters
        """

        if not self.supports_guest:  # pragma: no cover
            return adapters

        self.supports_guest = False

        with contextlib.suppress(LuciError):
            response_diag = await self.luci.wifi_diag_detail_all()
            _adapters_len: int = len(adapters)

            if "info" in response_diag:
                adapters += [
                    _adapter
                    for _adapter in response_diag["info"]
                    if "ifname" in _adapter and _adapter["ifname"] == IfName.WL14.value
                ]

            if _adapters_len < len(adapters):
                self.supports_guest = True

        return adapters

    @staticmethod
    def _prepare_wifi_data(data: dict) -> dict:
        """Prepare wifi data

        :param data:
        :return: dict: wifi data
        """

        wifi_data: dict = {}

        for data_field, field in ATTR_WIFI_DATA_FIELDS.items():
            if "channelInfo" in data_field and "channelInfo" in data:
                data_field = data_field.replace("channelInfo.", "")

                if data_field in data["channelInfo"]:
                    wifi_data[field] = data["channelInfo"][data_field]
            elif data_field in data:
                wifi_data[field] = data[data_field]

        return wifi_data

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

            data[f"{Wifi(index).phrase}_channels"] = [  # type: ignore
                str(channel["c"])
                for channel in response["list"]
                if "c" in channel and int(channel["c"]) > 0
            ]

    async def _async_prepare_devices(self, data: dict) -> None:
        """Prepare devices.

        :param data: dict
        """

        self.reset_counter()

        response: dict = await self.luci.wifi_connect_devices()

        if "list" in response:
            integrations: dict[str, dict] = {}

            if self.is_repeater and self.is_force_load:
                integrations = async_get_integrations(self.hass)

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

                    if ATTR_TRACKER_MAC in device:
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
                self.reset_counter(is_remove=True)

                data[ATTR_SENSOR_MODE] = Mode.MESH

                if self.is_force_load:
                    await self._async_prepare_devices(data)

            return

        integrations: dict[str, dict] = async_get_integrations(self.hass)

        mac_to_ip: dict[str, str] = {
            device[ATTR_TRACKER_MAC]: device["ip"][0]["ip"]
            for device in response["list"]
            if "ip" in device and len(device["ip"]) > 0 and ATTR_TRACKER_MAC in device
        }

        add_to: dict = {}

        self.reset_counter(is_force=True)

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

                if (
                    ATTR_TRACKER_MAC in device
                    and device[ATTR_TRACKER_MAC] not in integration[UPDATER].devices
                    and not integration[UPDATER].is_force_load
                ):
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

                    if integration[UPDATER].is_force_load:
                        continue
            else:
                device[ATTR_TRACKER_ENTRY_ID] = self._entry_id

                if (
                    ATTR_TRACKER_MAC in device
                    and device[ATTR_TRACKER_MAC] in self._moved_devices
                ):
                    device[ATTR_TRACKER_UPDATER_ENTRY_ID] = self._entry_id
                    device[ATTR_TRACKER_ROUTER_MAC_ADDRESS] = (
                        self.data.get(ATTR_DEVICE_MAC_ADDRESS, None),
                    )

                    if self._mass_update_device(device, integrations):
                        action = DeviceAction.SKIP

                    self._moved_devices.remove(device[ATTR_TRACKER_MAC])

            if (
                ATTR_TRACKER_MAC in device
                and device[ATTR_TRACKER_MAC] not in self._moved_devices
            ):
                device[ATTR_TRACKER_UPDATER_ENTRY_ID] = self._entry_id

                if ATTR_TRACKER_MAC in device:
                    self.add_device(device, action=action, integrations=integrations)

        if not add_to:
            return

        await asyncio.sleep(DEFAULT_CALL_DELAY)

        for _ip, devices in add_to.items():
            if not integrations[_ip][UPDATER].is_force_load:
                integrations[_ip][UPDATER].reset_counter(is_force=True)

            for device in devices.values():
                if ATTR_TRACKER_MAC in device[0]:
                    integrations[_ip][UPDATER].add_device(
                        device[0], True, device[1], integrations
                    )

    async def _async_prepare_device_restore(self, data: dict) -> None:
        """Restore devices

        :param data: dict
        """

        if not self._is_first_update or (self.is_repeater and self.is_force_load):
            return

        devices: dict | None = await self._async_load_devices()

        if devices is None:
            return

        integrations: dict = async_get_integrations(self.hass)

        for mac, device in devices.items():
            if mac in self.devices:
                continue

            try:
                # fmt: off
                device[ATTR_TRACKER_CONNECTION] = Connection(int(device[ATTR_TRACKER_CONNECTION])) \
                    if ATTR_TRACKER_CONNECTION in device \
                    and device[ATTR_TRACKER_CONNECTION] is not None \
                    else None
                # fmt: on
            except ValueError:
                device[ATTR_TRACKER_CONNECTION] = None

            _is_add: bool = True
            if device[ATTR_TRACKER_ENTRY_ID] != self._entry_id:
                for integration in integrations.values():
                    if (
                        integration[ATTR_TRACKER_ENTRY_ID]
                        != device[ATTR_TRACKER_ENTRY_ID]
                    ):
                        continue

                    if integration[UPDATER].is_force_load:
                        if mac in integration[UPDATER].devices:
                            integration[UPDATER].devices[mac] |= {
                                attr: device[attr]
                                for attr in [ATTR_TRACKER_NAME, ATTR_TRACKER_IP]
                                if attr in device and device[attr] is not None
                            }

                        _is_add = False

                        break

                    if mac not in integration[UPDATER].devices:
                        device |= {
                            ATTR_TRACKER_ROUTER_MAC_ADDRESS: integration[
                                UPDATER
                            ].data.get(
                                ATTR_DEVICE_MAC_ADDRESS,
                                device[ATTR_TRACKER_ROUTER_MAC_ADDRESS],
                            ),
                            ATTR_TRACKER_UPDATER_ENTRY_ID: self._entry_id,
                        }

                        integration[UPDATER].devices[mac] = device

                        self._moved_devices.append(mac)

                        break

            if not _is_add:
                continue

            if mac not in self._moved_devices:
                device |= {
                    ATTR_TRACKER_UPDATER_ENTRY_ID: self._entry_id,
                    ATTR_TRACKER_ENTRY_ID: self._entry_id,
                }

            self.devices[mac] = device

            async_dispatcher_send(
                self.hass, SIGNAL_NEW_DEVICE, device | {ATTR_TRACKER_IS_RESTORED: True}
            )

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

        is_new: bool = device[ATTR_TRACKER_MAC] not in self.devices

        _device: dict[str, Any] = self._build_device(device, integrations)

        if (
            self.is_repeater
            and self.is_force_load
            and device[ATTR_TRACKER_MAC] in self.devices
        ):
            self.devices[device[ATTR_TRACKER_MAC]] |= {
                key: value
                for key, value in _device.items()
                if (
                    (not is_from_parent and key not in REPEATER_SKIP_ATTRS)
                    or (is_from_parent and key in REPEATER_SKIP_ATTRS)
                )
                and value is not None
            }
        else:
            self.devices[device[ATTR_TRACKER_MAC]] = _device

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

        if device[ATTR_TRACKER_MAC] in self._moved_devices or (
            self.is_repeater and self.is_force_load
        ):
            return

        self.data[ATTR_SENSOR_DEVICES] += 1

        code: str = _device.get(ATTR_TRACKER_CONNECTION, Connection.LAN).name.replace(
            "WIFI_", ""
        )
        code = f"{ATTR_SENSOR_DEVICES}_{code}".lower()

        self.data[code] += 1

    def _build_device(
        self, device: dict, integrations: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Build device

        :param device: dict
        :param integrations: dict[str, Any]: Integrations list
        :return dict[str, Any]
        """

        ip_attr: dict | None = device["ip"][0] if "ip" in device else None

        if self.is_force_load and "wifiIndex" in device:
            device["type"] = 6 if device["wifiIndex"] == 3 else device["wifiIndex"]

        connection: Connection | None = None

        with contextlib.suppress(ValueError):
            # fmt: off
            connection = Connection(int(device["type"])) \
                if "type" in device else None
            # fmt: on

        return {
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
            ATTR_TRACKER_NAME: device.get("name", device[ATTR_TRACKER_MAC]),
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

    def _mass_update_device(self, device: dict, integrations: dict) -> bool:
        """Mass update devices

        :param device: dict: Device data
        :param integrations: dict: Integration list
        :return bool: is found
        """

        is_found: bool = False

        for _ip, integration in integrations.items():
            if (
                device[ATTR_TRACKER_MAC] not in integration[UPDATER].devices
                or _ip == self.ip
            ):
                continue

            _device: dict[str, Any] = self._build_device(device, integrations)
            if self.is_repeater and self.is_force_load:
                for attr in REPEATER_SKIP_ATTRS:
                    if attr in _device:
                        del _device[attr]

            integration[UPDATER].devices[device[ATTR_TRACKER_MAC]] |= _device
            is_found = True

        return is_found

    async def _async_prepare_ap(self, data: dict) -> None:
        """Prepare wifi ap.

        :param data: dict
        """

        if self.data.get(ATTR_SENSOR_MODE, Mode.DEFAULT) != Mode.REPEATER:
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

        if "count" in response:
            data[ATTR_SENSOR_DEVICES] = response["count"]

        for key, attr in NEW_STATUS_MAP.items():
            if key in response and "online_sta_count" in response[key]:
                data[attr] = response[key]["online_sta_count"]

        _other_devices = sum(
            int(data[attr]) for attr in NEW_STATUS_MAP.values() if attr in data
        )

        if _other_devices > 0 and ATTR_SENSOR_DEVICES in data:
            _other_devices = int(data[ATTR_SENSOR_DEVICES]) - _other_devices

            data[ATTR_SENSOR_DEVICES_LAN] = max(_other_devices, 0)

    def _clean_devices(self) -> None:
        """Clean devices."""

        if self._activity_days == 0 or len(self.devices) == 0:
            return

        now = datetime.now().replace(microsecond=0)
        devices: dict = self.devices.copy()

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

            del self.devices[mac]

    def reset_counter(self, is_force: bool = False, is_remove: bool = False) -> None:
        """Reset counter

        :param is_force: bool: Force reset
        :param is_remove: bool: Force remove
        """

        if self.is_repeater and not self.is_force_load and not is_force:
            return

        for attr in [
            ATTR_SENSOR_DEVICES,
            ATTR_SENSOR_DEVICES_LAN,
            ATTR_SENSOR_DEVICES_GUEST,
            ATTR_SENSOR_DEVICES_2_4,
            ATTR_SENSOR_DEVICES_5_0,
            ATTR_SENSOR_DEVICES_5_0_GAME,
        ]:
            if attr in self.data and is_remove:
                del self.data[attr]
            elif not is_remove:
                self.data[attr] = 0

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


@callback
def async_get_integrations(hass: HomeAssistant) -> dict[str, dict]:
    """Return integrations map.

    :param hass: HomeAssistant
    :return dict[str, dict]
    """

    return {
        integration[CONF_IP_ADDRESS]: {
            UPDATER: integration[UPDATER],
            ATTR_TRACKER_ENTRY_ID: entry_id,
        }
        for entry_id, integration in hass.data[DOMAIN].items()
        if isinstance(integration, dict)
    }


@callback
def async_get_updater(hass: HomeAssistant, identifier: str) -> LuciUpdater:
    """Return LuciUpdater for ip address or entry id.

    :param hass: HomeAssistant
    :param identifier: str
    :return LuciUpdater
    """

    _error: str = f"Integration with identifier: {identifier} not found."

    if DOMAIN not in hass.data:
        raise ValueError(_error)

    if identifier in hass.data[DOMAIN] and UPDATER in hass.data[DOMAIN][identifier]:
        return hass.data[DOMAIN][identifier][UPDATER]

    if integrations := [
        integration[UPDATER]
        for integration in hass.data[DOMAIN].values()
        if isinstance(integration, dict) and integration[CONF_IP_ADDRESS] == identifier
    ]:
        return integrations[0]

    raise ValueError(_error)
