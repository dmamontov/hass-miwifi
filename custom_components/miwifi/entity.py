"""MiWifi entity."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_DEVICE_MAC_ADDRESS, ATTR_STATE, ATTRIBUTION
from .helper import generate_entity_id
from .updater import LuciUpdater

_LOGGER = logging.getLogger(__name__)

ROUTER_ATTRIBUTE_KEYS: tuple[str, ...] = (
    "device_name",
    "device_model",
    "device_manufacturer",
    "device_sw_version",
    "device_mac_address",
    "device_hw_version",
    "current_version",
    "uptime",
    "memory_usage",
    "memory_total",
    "temperature",
    "wan_download_speed",
    "wan_upload_speed",
    "vpn_uptime",
    "vpn_state",
    "mode",
    "dual_band",
    "wan_state",
    "led",
    "devices",
    "devices_lan",
    "devices_guest",
    "devices_2_4",
    "devices_5_0",
    "devices_5_0_game",
    "wifi_2_4",
    "wifi_2_4_channel",
    "wifi_2_4_signal_strength",
    "wifi_5_0",
    "wifi_5_0_channel",
    "wifi_5_0_signal_strength",
    "wifi_guest",
    "wifi_adapter_length",
    "wifi_2_4_channels",
    "wifi_5_0_channels",
)


def _serialize_router_value(value: Any) -> Any:
    """Serialize router data for HA state attributes."""

    if isinstance(value, Enum):
        return getattr(value, "phrase", str(value))

    if isinstance(value, dict):
        return {key: _serialize_router_value(val) for key, val in value.items()}

    if isinstance(value, list):
        return [_serialize_router_value(item) for item in value]

    return value


class MiWifiEntity(CoordinatorEntity):
    """MiWifi entity."""

    _attr_attribution: str = ATTRIBUTION

    def __init__(
        self,
        unique_id: str,
        description: EntityDescription,
        updater: LuciUpdater,
        entity_id_format: str,
    ) -> None:
        """Initialize sensor.

        :param unique_id: str: Unique ID
        :param description: EntityDescription: EntityDescription object
        :param updater: LuciUpdater: Luci updater object
        :param entity_id_format: str: ENTITY_ID_FORMAT
        """

        CoordinatorEntity.__init__(self, coordinator=updater)

        self.entity_description = description
        self._updater: LuciUpdater = updater

        self.entity_id = generate_entity_id(
            entity_id_format,
            updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip),
            description.name,
        )

        self._attr_name = description.name
        self._attr_unique_id = unique_id
        self._attr_available = updater.data.get(ATTR_STATE, False)

        self._attr_device_info = updater.device_info

    def _router_extra_state_attributes(self) -> dict[str, Any]:
        """Return a safe router-level snapshot for automations and templates."""

        attrs: dict[str, Any] = {}
        for key in ROUTER_ATTRIBUTE_KEYS:
            if key in self._updater.data:
                attrs[key] = _serialize_router_value(self._updater.data[key])

        firmware = self._updater.data.get("firmware")
        if isinstance(firmware, dict):
            attrs["firmware"] = _serialize_router_value(firmware)

        return attrs

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""

        await CoordinatorEntity.async_added_to_hass(self)

    @property
    def available(self) -> bool:
        """Is available

        :return bool: Is available
        """

        return self._attr_available and self.coordinator.last_update_success

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        raise NotImplementedError  # pragma: no cover
