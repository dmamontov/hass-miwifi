"""Sensor component."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Final

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ENTITY_CATEGORY_DIAGNOSTIC,
    PERCENTAGE,
    DATA_MEGABYTES,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    UPDATER,
    ATTRIBUTION,
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_STATE,
    ATTR_WIFI_ADAPTER_LENGTH,
    ATTR_SENSOR_UPTIME,
    ATTR_SENSOR_UPTIME_NAME,
    ATTR_SENSOR_MEMORY_USAGE,
    ATTR_SENSOR_MEMORY_USAGE_NAME,
    ATTR_SENSOR_MEMORY_TOTAL,
    ATTR_SENSOR_MEMORY_TOTAL_NAME,
    ATTR_SENSOR_TEMPERATURE,
    ATTR_SENSOR_TEMPERATURE_NAME,
    ATTR_SENSOR_MODE,
    ATTR_SENSOR_MODE_NAME,
    ATTR_SENSOR_DEVICES,
    ATTR_SENSOR_DEVICES_NAME,
    ATTR_SENSOR_DEVICES_LAN,
    ATTR_SENSOR_DEVICES_LAN_NAME,
    ATTR_SENSOR_DEVICES_GUEST,
    ATTR_SENSOR_DEVICES_GUEST_NAME,
    ATTR_SENSOR_DEVICES_2_4,
    ATTR_SENSOR_DEVICES_2_4_NAME,
    ATTR_SENSOR_DEVICES_5_0,
    ATTR_SENSOR_DEVICES_5_0_NAME,
    ATTR_SENSOR_DEVICES_5_0_GAME,
    ATTR_SENSOR_DEVICES_5_0_GAME_NAME,
)
from .helper import generate_entity_id
from .updater import LuciUpdater

PCS: Final = "pcs"

MIWIFI_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=ATTR_SENSOR_UPTIME,
        name=ATTR_SENSOR_UPTIME_NAME,
        icon="mdi:timer-sand",
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=ATTR_SENSOR_MEMORY_USAGE,
        name=ATTR_SENSOR_MEMORY_USAGE_NAME,
        icon="mdi:memory",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=ATTR_SENSOR_MEMORY_TOTAL,
        name=ATTR_SENSOR_MEMORY_TOTAL_NAME,
        icon="mdi:memory",
        native_unit_of_measurement=DATA_MEGABYTES,
        state_class=SensorStateClass.TOTAL,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=ATTR_SENSOR_TEMPERATURE,
        name=ATTR_SENSOR_TEMPERATURE_NAME,
        icon="mdi:timer-sand",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=ATTR_SENSOR_MODE,
        name=ATTR_SENSOR_MODE_NAME,
        icon="mdi:transit-connection-variant",
        state_class=SensorStateClass.TOTAL,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    SensorEntityDescription(
        key=ATTR_SENSOR_DEVICES,
        name=ATTR_SENSOR_DEVICES_NAME,
        icon="mdi:counter",
        native_unit_of_measurement=PCS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=True,
    ),
    SensorEntityDescription(
        key=ATTR_SENSOR_DEVICES_LAN,
        name=ATTR_SENSOR_DEVICES_LAN_NAME,
        icon="mdi:counter",
        native_unit_of_measurement=PCS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=ATTR_SENSOR_DEVICES_GUEST,
        name=ATTR_SENSOR_DEVICES_GUEST_NAME,
        icon="mdi:counter",
        native_unit_of_measurement=PCS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=ATTR_SENSOR_DEVICES_2_4,
        name=ATTR_SENSOR_DEVICES_2_4_NAME,
        icon="mdi:counter",
        native_unit_of_measurement=PCS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=ATTR_SENSOR_DEVICES_5_0,
        name=ATTR_SENSOR_DEVICES_5_0_NAME,
        icon="mdi:counter",
        native_unit_of_measurement=PCS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=ATTR_SENSOR_DEVICES_5_0_GAME,
        name=ATTR_SENSOR_DEVICES_5_0_GAME_NAME,
        icon="mdi:counter",
        native_unit_of_measurement=PCS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MiWifi sensor entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: ConfigEntry object
    :param async_add_entities: AddEntitiesCallback: AddEntitiesCallback callback object
    """

    data: dict = hass.data[DOMAIN][config_entry.entry_id]
    updater: LuciUpdater = data[UPDATER]

    if not updater.data.get(ATTR_DEVICE_MAC_ADDRESS, False):
        _LOGGER.error("Failed to initialize sensor: Missing mac address. Restart HASS.")

    entities: list[MiWifiSensor] = [
        MiWifiSensor(
            f"{config_entry.unique_id}-{description.key}",
            description,
            updater,
        )
        for description in MIWIFI_SENSORS
        if description.key != ATTR_SENSOR_DEVICES_5_0_GAME
           or updater.data.get(ATTR_WIFI_ADAPTER_LENGTH, 3) == 3
    ]
    async_add_entities(entities)


class MiWifiSensor(SensorEntity, CoordinatorEntity, RestoreEntity):
    """MiWifi binary sensor entry."""

    _attr_attribution: str = ATTRIBUTION

    def __init__(
            self,
            unique_id: str,
            description: SensorEntityDescription,
            updater: LuciUpdater,
    ) -> None:
        """Initialize sensor.

        :param unique_id: str: Unique ID
        :param description: SensorEntityDescription: SensorEntityDescription object
        :param updater: LuciUpdater: Luci updater object
        """

        CoordinatorEntity.__init__(self, coordinator=updater)
        RestoreEntity.__init__(self)

        self.entity_description = description
        self._updater: LuciUpdater = updater

        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip),
            description.name,
        )

        self._attr_name = description.name
        self._attr_unique_id = unique_id

        self._attr_device_info = updater.device_info

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""

        await RestoreEntity.async_added_to_hass(self)
        await CoordinatorEntity.async_added_to_hass(self)

        state = await self.async_get_last_state()
        if not state:
            return

        self._attr_native_value = state.state

        self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        is_available: bool = self._updater.data.get(ATTR_STATE, False)

        state: Any = self._updater.data.get(self.entity_description.key, None)

        if state is not None and isinstance(state, Enum):
            state = state.phrase

        if self._attr_native_value == state and self._attr_available == is_available:
            return

        self._attr_available = is_available
        self._attr_native_value = state

        self.async_write_ha_state()
