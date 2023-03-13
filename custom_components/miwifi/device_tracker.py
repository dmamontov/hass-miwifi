"""Device tracker component."""

from __future__ import annotations

import logging
import socket
import time
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
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    EntityPlatform,
    async_get_current_platform,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_STATE,
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
    ATTR_TRACKER_SCANNER,
    ATTR_TRACKER_SIGNAL,
    ATTR_TRACKER_UP_SPEED,
    ATTR_TRACKER_UPDATER_ENTRY_ID,
    ATTRIBUTION,
    CONF_IS_TRACK_DEVICES,
    CONF_STAY_ONLINE,
    DEFAULT_CALL_DELAY,
    DEFAULT_STAY_ONLINE,
    DOMAIN,
    SIGNAL_NEW_DEVICE,
    UPDATER,
)
from .enum import Connection, DeviceClass
from .helper import (
    detect_manufacturer,
    generate_entity_id,
    get_config_value,
    parse_last_activity,
    pretty_size,
)
from .updater import LuciUpdater, async_get_updater

PARALLEL_UPDATES = 0

ATTR_CHANGES: Final = (
    ATTR_TRACKER_IP,
    ATTR_TRACKER_ONLINE,
    ATTR_TRACKER_CONNECTION,
    ATTR_TRACKER_ROUTER_MAC_ADDRESS,
    ATTR_TRACKER_SIGNAL,
    ATTR_TRACKER_DOWN_SPEED,
    ATTR_TRACKER_UP_SPEED,
    ATTR_TRACKER_OPTIONAL_MAC,
)

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

    updater: LuciUpdater = async_get_updater(hass, config_entry.entry_id)

    @callback
    def add_device(new_device: dict) -> None:
        """Add device.

        :param new_device: dict: Device object
        """

        if (
            not get_config_value(config_entry, CONF_IS_TRACK_DEVICES, True)
            or new_device[ATTR_TRACKER_UPDATER_ENTRY_ID] != config_entry.entry_id
        ):
            return  # pragma: no cover

        entity_id: str = generate_entity_id(
            ENTITY_ID_FORMAT, str(new_device.get(ATTR_TRACKER_MAC))
        )

        try:
            platform: EntityPlatform = async_get_current_platform()
        except RuntimeError as _e:  # pragma: no cover
            _LOGGER.debug("An error occurred while adding the device: %r", _e)

            return

        if entity_id in platform.entities:  # pragma: no cover
            _LOGGER.debug("Device already added: %s", entity_id)

            return

        async_add_entities(
            [
                MiWifiDeviceTracker(
                    f"{DOMAIN}-{device.get(ATTR_TRACKER_MAC)}",
                    entity_id,
                    new_device,
                    updater,
                    get_config_value(
                        config_entry, CONF_STAY_ONLINE, DEFAULT_STAY_ONLINE
                    ),
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
    _attr_device_class: str = DeviceClass.DEVICE_TRACKER

    _configuration_port: int | None = None
    _is_connected: bool = False

    def __init__(  # pylint: disable=too-many-arguments
        self,
        unique_id: str,
        entity_id: str,
        device: dict,
        updater: LuciUpdater,
        stay_online: int,
    ) -> None:
        """Initialize device_tracker.

        :param unique_id: str: Unique ID
        :param entity_id: str: Entity ID
        :param device: dict: Device data
        :param updater: LuciUpdater: Luci updater object
        :param stay_online: int: Stay online
        """

        CoordinatorEntity.__init__(self, coordinator=updater)

        self._device: dict = dict(device)
        self._updater: LuciUpdater = updater

        self._attr_name = device.get(ATTR_TRACKER_NAME, self.mac_address)

        self._stay_online: int = stay_online

        self.entity_id = entity_id
        self._attr_unique_id = unique_id
        self._attr_available = updater.data.get(ATTR_STATE, False)

        if self._attr_available:
            self._is_connected = not device.get(ATTR_TRACKER_IS_RESTORED, False)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""

        await CoordinatorEntity.async_added_to_hass(self)

        self.hass.loop.call_later(
            DEFAULT_CALL_DELAY,
            lambda: self.hass.async_create_task(self.check_ports()),
        )

    @property
    def available(self) -> bool:
        """Is available

        :return bool: Is available
        """

        return self._attr_available and self.coordinator.last_update_success

    @cached_property
    def mac_address(self) -> str:
        """Return the mac address of the device.

        :return str | None: Mac address
        """

        return str(self._device.get(ATTR_TRACKER_MAC))

    @property
    def manufacturer(self) -> str | None:
        """Return manufacturer of the device.

        :return str | None: Manufacturer
        """

        return detect_manufacturer(self.mac_address)

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

        if not self.is_connected or connection == Connection.LAN:
            signal = ""

        if connection is not None and isinstance(connection, Connection):
            connection = connection.phrase  # type: ignore

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

        _schema: str = "https" if self._configuration_port == 443 else "http"

        return (
            f"{_schema}://{self.ip_address}"
            if self._configuration_port in [80, 443]
            else f"{_schema}://{self.ip_address}:{self._configuration_port}"
        )

    @property
    def device_info(self) -> DeviceInfo:  # pylint: disable=overridden-final-method
        """Return device info.

        :return DeviceInfo: Device Info
        """

        _optional_mac = self._device.get(ATTR_TRACKER_OPTIONAL_MAC, None)
        if _optional_mac is not None:
            return DeviceInfo(
                connections={
                    (dr.CONNECTION_NETWORK_MAC, self.mac_address),
                    (dr.CONNECTION_NETWORK_MAC, _optional_mac),
                },
                identifiers={(DOMAIN, self.mac_address)},
                name=self._attr_name,
            )

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
            if self._attr_available:  # type: ignore
                self._attr_available = False

                self.async_write_ha_state()

            return

        device = self._update_entry(device)

        before: int = parse_last_activity(
            str(self._device.get(ATTR_TRACKER_LAST_ACTIVITY))
        )
        current: int = parse_last_activity(str(device.get(ATTR_TRACKER_LAST_ACTIVITY)))

        is_connected = current > before

        if before == current:
            is_connected = (int(time.time()) - current) <= self._stay_online

        attr_changed: list = [
            attr
            for attr in ATTR_CHANGES
            if self._device.get(attr, None) != device.get(attr, None)
        ]

        if (
            self._attr_available == is_available
            and self._is_connected == is_connected
            and not attr_changed
        ):
            return

        self._attr_available = is_available
        self._is_connected = is_connected
        self._device = dict(device)

        self.async_write_ha_state()

    def _update_entry(self, track_device: dict) -> dict:
        """Update device entry.

        :param track_device: dict: Track device
        :return dict
        """

        entry_id: str | None = track_device.get(ATTR_TRACKER_ENTRY_ID)

        device_registry: dr.DeviceRegistry = dr.async_get(self.hass)
        device: dr.DeviceEntry | None = device_registry.async_get_device(
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

        if (
            entry_id in self.hass.data[DOMAIN]
            and self._updater != self.hass.data[DOMAIN][entry_id][UPDATER]
        ):
            self._updater = self.hass.data[DOMAIN][entry_id][UPDATER]
            self._device[ATTR_TRACKER_ENTRY_ID] = entry_id
            track_device = self._updater.devices.get(self.mac_address, track_device)

        return track_device

    async def check_ports(self) -> None:
        """Scan port to configuration url"""

        if self.ip_address is None:
            return

        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(5)

            for port in CONFIGURATION_PORTS:
                result = sock.connect_ex((self.ip_address, port))
                if result == 0:
                    self._configuration_port = port

                    _LOGGER.debug("Found open port %s: %s", self.ip_address, port)

                    break
