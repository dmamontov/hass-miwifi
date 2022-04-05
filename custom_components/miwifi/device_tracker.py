"""Device tracker component."""

from __future__ import annotations

import logging
import socket
from contextlib import closing
from functools import cached_property
from typing import Any, Final

from homeassistant.components.device_tracker import ENTITY_ID_FORMAT, SOURCE_TYPE_ROUTER
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    UPDATER,
    DEFAULT_CALL_DELAY,
    SIGNAL_NEW_DEVICE,
    ATTRIBUTION,
    ATTR_STATE,
    ATTR_TRACKER_ENTRY_ID,
    ATTR_TRACKER_UPDATER_ENTRY_ID,
    ATTR_TRACKER_SCANNER,
    ATTR_TRACKER_MAC,
    ATTR_TRACKER_ROUTER_MAC_ADDRESS,
    ATTR_TRACKER_SIGNAL,
    ATTR_TRACKER_NAME,
    ATTR_TRACKER_CONNECTION,
    ATTR_TRACKER_IP,
    ATTR_TRACKER_ONLINE,
    ATTR_TRACKER_DOWN_SPEED,
    ATTR_TRACKER_UP_SPEED,
    ATTR_TRACKER_LAST_ACTIVITY,
)
from .enum import Connection
from .helper import generate_entity_id, parse_last_activity, pretty_size
from .updater import LuciUpdater

ATTR_CHANGES: Final = [
    ATTR_TRACKER_IP,
    ATTR_TRACKER_ONLINE,
    ATTR_TRACKER_CONNECTION,
    ATTR_TRACKER_ROUTER_MAC_ADDRESS,
    ATTR_TRACKER_SIGNAL,
    ATTR_TRACKER_DOWN_SPEED,
    ATTR_TRACKER_UP_SPEED,
]

CONFIGURATION_PORTS: Final = [80, 443]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MiWifi device tracker entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: ConfigEntry object
    :param async_add_entities: AddEntitiesCallback: Async add callback
    """

    data: dict = hass.data[DOMAIN][config_entry.entry_id]
    updater: LuciUpdater = data[UPDATER]

    @callback
    def add_device(device: dict) -> None:
        """Add device.

        :param device: dict: Device object
        """

        if device[ATTR_TRACKER_UPDATER_ENTRY_ID] != config_entry.entry_id:
            return

        async_add_entities(
            [
                MiWifiDeviceTracker(
                    f"{DOMAIN}-{device.get(ATTR_TRACKER_MAC)}", device, updater
                )
            ]
        )

    for device in updater.devices.values():
        add_device(device)

    updater.new_device_callback = async_dispatcher_connect(
        hass, SIGNAL_NEW_DEVICE, add_device
    )


class MiWifiDeviceTracker(ScannerEntity, CoordinatorEntity):
    """MiWifi device tracker entry."""

    _attr_attribution: str = ATTRIBUTION
    _configuration_port: int | None = None
    _is_connected: bool = False
    _device: dict

    def __init__(
        self,
        unique_id: str,
        device: dict,
        updater: LuciUpdater,
    ) -> None:
        """Initialize device_tracker.

        :param unique_id: str: Unique ID
        :param device: dict: Device data
        :param updater: LuciUpdater: Luci updater object
        """

        CoordinatorEntity.__init__(self, coordinator=updater)

        self._device = device
        self._updater = updater

        self._attr_name = device.get(ATTR_TRACKER_NAME, self.mac_address)

        self.entity_id = generate_entity_id(ENTITY_ID_FORMAT, self.mac_address)

        self._attr_unique_id = unique_id

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""

        await CoordinatorEntity.async_added_to_hass(self)

        self.hass.loop.call_later(
            DEFAULT_CALL_DELAY,
            lambda: self.hass.async_create_task(self.check_ports()),
        )

    @cached_property
    def mac_address(self) -> str | None:
        """Return the mac address of the device.

        :return str | None: Mac address
        """

        return self._device.get(ATTR_TRACKER_MAC, None)

    @property
    def manufacturer(self) -> str | None:
        """Return manufacturer of the device.

        :return str | None: Manufacturer
        """

        return self._updater.manufacturer(self.mac_address)

    @property
    def ip_address(self) -> str | None:
        """Return the primary ip address of the device.

        :return str | None: IP address
        """

        return self._device.get(ATTR_TRACKER_IP, None)

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected to the network.

        :return bool: Is connected
        """

        return self._is_connected

    @cached_property
    def unique_id(self) -> str:
        """Return unique ID of the entity.

        :return str: Unique ID
        """

        return self._attr_unique_id

    @property
    def icon(self) -> str:
        """Return device icon.

        :return str: Default icon
        """

        return "mdi:lan-connect" if self.is_connected else "mdi:lan-disconnect"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes.

        :return dict[str, Any]: Extra state attributes
        """

        signal: Any = self._device.get(ATTR_TRACKER_SIGNAL, "")
        connection: Any = self._device.get(ATTR_TRACKER_CONNECTION, None)

        if isinstance(connection, int):
            try:
                connection = Connection(connection)
            except ValueError:
                connection = None

        if not self.is_connected or connection == Connection.LAN:
            signal = ""

        if connection is not None and isinstance(connection, Connection):
            connection = connection.phrase

        return {
            ATTR_TRACKER_SCANNER: DOMAIN,
            ATTR_TRACKER_MAC: self.mac_address,
            ATTR_TRACKER_IP: self.ip_address,
            ATTR_TRACKER_ONLINE: self._device.get(ATTR_TRACKER_ONLINE, None)
            if self.is_connected
            else "",
            ATTR_TRACKER_CONNECTION: connection,
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: self._device.get(
                ATTR_TRACKER_ROUTER_MAC_ADDRESS, None
            ),
            ATTR_TRACKER_SIGNAL: signal,
            ATTR_TRACKER_DOWN_SPEED: pretty_size(
                float(self._device.get(ATTR_TRACKER_DOWN_SPEED, 0.0))
            )
            if self.is_connected
            else "",
            ATTR_TRACKER_UP_SPEED: pretty_size(
                float(self._device.get(ATTR_TRACKER_UP_SPEED, 0.0))
            )
            if self.is_connected
            else "",
            ATTR_TRACKER_LAST_ACTIVITY: self._device.get(
                ATTR_TRACKER_LAST_ACTIVITY, None
            ),
        }

    @property
    def configuration_url(self) -> str | None:
        """Configuration url

        :return str | None: Url
        """

        if self._configuration_port is None:
            return None

        if self._configuration_port == 80:
            return f"http://{self.ip_address}"

        if self._configuration_port == 443:
            return f"https://{self.ip_address}"

        return f"http://{self.ip_address}:{self._configuration_port}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info.

        :return DeviceInfo: Device Info
        """

        return DeviceInfo(
            connections={(dr.CONNECTION_NETWORK_MAC, self.mac_address)},
            identifiers={(DOMAIN, self.mac_address)},
            name=self._attr_name,
            configuration_url=self.configuration_url,
            manufacturer=self.manufacturer,
        )

    @cached_property
    def source_type(self) -> str:
        """Return source type.

        :return str: Source type router
        """

        return SOURCE_TYPE_ROUTER

    @cached_property
    def entity_registry_enabled_default(self) -> bool:
        """Return if entity is enabled by default.

        :return bool: Force enabled
        """

        return True

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        is_available: bool = self._updater.data.get(ATTR_STATE, False)
        device = self._updater.devices.get(self.mac_address, None)

        if device is None or self._device is None:
            if self._attr_available:
                self._attr_available = False

                self.async_write_ha_state()

            return

        self._update_entry(device.get(ATTR_TRACKER_ENTRY_ID, None))

        if not device.get(ATTR_TRACKER_LAST_ACTIVITY, False):
            is_connected = False
        elif not self._device.get(ATTR_TRACKER_LAST_ACTIVITY, False):
            is_connected = True
        else:
            is_connected = parse_last_activity(
                device.get(ATTR_TRACKER_LAST_ACTIVITY)
            ) > parse_last_activity(self._device.get(ATTR_TRACKER_LAST_ACTIVITY))

        is_update = False
        for attr in ATTR_CHANGES:
            if self._device.get(attr, None) != device.get(attr, None):
                is_update = True

                break

        if (
            self._attr_available == is_available
            and self._is_connected == is_connected
            and not is_update
        ):
            return

        self._attr_available = is_available
        self._is_connected = is_connected
        self._device = device

        self.async_write_ha_state()

    def _update_entry(self, entry_id: str) -> None:
        """Update device entry.

        :param entry_id: str: To entry id
        """

        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(
            set(), {(dr.CONNECTION_NETWORK_MAC, self.mac_address)}
        )

        if device is not None:
            if len(device.config_entries) > 0 and entry_id not in device.config_entries:
                device_registry.async_update_device(
                    device.id, add_config_entry_id=entry_id
                )

            if device.configuration_url is None and self.configuration_url is not None:
                device_registry.async_update_device(
                    device.id, configuration_url=self.configuration_url
                )

            if device.manufacturer is None and self.manufacturer is not None:
                device_registry.async_update_device(
                    device.id, manufacturer=self.manufacturer
                )

        if self._updater == self.hass.data[DOMAIN][entry_id][UPDATER]:
            return

        self._updater = self.hass.data[DOMAIN][entry_id][UPDATER]
        self._device[ATTR_TRACKER_ENTRY_ID] = entry_id

    async def check_ports(self) -> None:
        """Scan port to configuration url"""

        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(5)

            for port in CONFIGURATION_PORTS:
                if not isinstance(self.ip_address, str):
                    break

                result = sock.connect_ex((self.ip_address, port))
                if result == 0:
                    self._configuration_port = port

                    break

            if self._configuration_port is not None:
                _LOGGER.debug(
                    "Found open port %s: %s", self.ip_address, self._configuration_port
                )
