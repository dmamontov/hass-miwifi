"""Binary sensor component."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT,
    BinarySensorEntityDescription,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    UPDATER,
    ATTRIBUTION,
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_STATE,
    ATTR_STATE_NAME,
    ATTR_BINARY_SENSOR_WAN_STATE,
    ATTR_BINARY_SENSOR_WAN_STATE_NAME,
    ATTR_BINARY_SENSOR_DUAL_BAND,
    ATTR_BINARY_SENSOR_DUAL_BAND_NAME,
)
from .helper import generate_entity_id
from .updater import LuciUpdater

ICONS: Final = {
    f"{ATTR_STATE}_{STATE_ON}": "mdi:router-wireless",
    f"{ATTR_STATE}_{STATE_OFF}": "router-wireless-off",
}

MIWIFI_BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key=ATTR_STATE,
        name=ATTR_STATE_NAME,
        icon=ICONS[f"{ATTR_STATE}_{STATE_ON}"],
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    BinarySensorEntityDescription(
        key=ATTR_BINARY_SENSOR_WAN_STATE,
        name=ATTR_BINARY_SENSOR_WAN_STATE_NAME,
        icon="mdi:wan",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    BinarySensorEntityDescription(
        key=ATTR_BINARY_SENSOR_DUAL_BAND,
        name=ATTR_BINARY_SENSOR_DUAL_BAND_NAME,
        icon="mdi:wifi-plus",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MiWifi binary sensor entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: Config Entry object
    :param async_add_entities: AddEntitiesCallback: Async add callback
    """

    data: dict = hass.data[DOMAIN][config_entry.entry_id]
    updater: LuciUpdater = data[UPDATER]

    if not updater.data.get(ATTR_DEVICE_MAC_ADDRESS, False):
        _LOGGER.error(
            "Failed to initialize binary sensor: Missing mac address. Restart HASS."
        )

    entities: list[MiWifiBinarySensor] = [
        MiWifiBinarySensor(
            f"{config_entry.entry_id}-{description.key}",
            description,
            updater,
        )
        for description in MIWIFI_BINARY_SENSORS
    ]
    async_add_entities(entities)


class MiWifiBinarySensor(BinarySensorEntity, CoordinatorEntity, RestoreEntity):
    """MiWifi binary sensor entry."""

    _attr_attribution: str = ATTRIBUTION

    def __init__(
        self,
        unique_id: str,
        description: BinarySensorEntityDescription,
        updater: LuciUpdater,
    ) -> None:
        """Initialize sensor.

        :param unique_id: str: Unique ID
        :param description: BinarySensorEntityDescription: BinarySensorEntityDescription object
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

        self._attr_is_on = state.state == STATE_ON

        self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        # fmt: off
        is_available: bool = self._updater.data.get(ATTR_STATE, False) \
            if self.entity_description.key != ATTR_STATE \
            else True
        # fmt: on

        is_on: bool = self._updater.data.get(self.entity_description.key, False)

        if self._attr_is_on == is_on and self._attr_available == is_available:  # type: ignore
            return

        self._attr_available = is_available
        self._attr_is_on = is_on

        icon_name: str = "{}_{}".format(
            self.entity_description.key, STATE_ON if is_on else STATE_OFF
        )

        if icon_name in ICONS:
            self._attr_icon = ICONS[icon_name]

        self.async_write_ha_state()
