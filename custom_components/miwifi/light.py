"""Light component."""

from __future__ import annotations

import logging
from typing import Final, Any

from homeassistant.components.light import (
    ENTITY_ID_FORMAT,
    LightEntityDescription,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    UPDATER,
    ATTRIBUTION,
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_STATE,
    ATTR_LIGHT_LED,
    ATTR_LIGHT_LED_NAME,
)
from .exceptions import LuciException
from .helper import generate_entity_id
from .updater import LuciUpdater

ICONS: Final = {
    f"{ATTR_LIGHT_LED}_{STATE_ON}": "mdi:led-on",
    f"{ATTR_LIGHT_LED}_{STATE_OFF}": "mdi:led-off",
}

MIWIFI_LIGHTS: tuple[LightEntityDescription, ...] = (
    LightEntityDescription(
        key=ATTR_LIGHT_LED,
        name=ATTR_LIGHT_LED_NAME,
        icon=ICONS[f"{ATTR_LIGHT_LED}_{STATE_ON}"],
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=True,
    ),
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MiWifi light entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: ConfigEntry object
    :param async_add_entities: AddEntitiesCallback: AddEntitiesCallback callback object
    """

    data: dict = hass.data[DOMAIN][config_entry.entry_id]
    updater: LuciUpdater = data[UPDATER]

    entities: list[MiWifiLight] = [
        MiWifiLight(
            f"{config_entry.entry_id}-{description.key}",
            description,
            updater,
        )
        for description in MIWIFI_LIGHTS
    ]
    async_add_entities(entities)


class MiWifiLight(LightEntity, CoordinatorEntity):
    """MiWifi light entry."""

    _attr_attribution: str = ATTRIBUTION

    def __init__(
        self,
        unique_id: str,
        description: LightEntityDescription,
        updater: LuciUpdater,
    ) -> None:
        """Initialize light.

        :param unique_id: str: Unique ID
        :param description: LightEntityDescription: LightEntityDescription object
        :param updater: LuciUpdater: Luci updater object
        """

        CoordinatorEntity.__init__(self, coordinator=updater)

        self.entity_description = description
        self._updater = updater

        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip),
            description.name,
        )

        self._attr_name = description.name
        self._attr_unique_id = unique_id
        self._attr_available = updater.data.get(ATTR_STATE, False)

        self._attr_device_info = updater.device_info

        self._attr_is_on = updater.data.get(description.key, False)
        self._change_icon(self._attr_is_on)

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

        is_available: bool = self._updater.data.get(ATTR_STATE, False)

        is_on: bool = self._updater.data.get(self.entity_description.key, False)

        if self._attr_is_on == is_on and self._attr_available == is_available:  # type: ignore
            return

        self._attr_available = is_available
        self._attr_is_on = is_on

        self._change_icon(is_on)

        self.async_write_ha_state()

    async def _led_on(self) -> None:
        """Led on action"""

        try:
            await self._updater.luci.led(1)
        except LuciException:
            pass

    async def _led_off(self) -> None:
        """Led off action"""

        try:
            await self._updater.luci.led(0)
        except LuciException:
            pass

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on action

        :param kwargs: Any: Any arguments
        """

        await self._async_call(
            f"_{self.entity_description.key}_{STATE_ON}", STATE_ON, **kwargs
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off action

        :param kwargs: Any: Any arguments
        """

        await self._async_call(
            f"_{self.entity_description.key}_{STATE_OFF}", STATE_OFF, **kwargs
        )

    async def _async_call(self, method: str, state: str, **kwargs: Any) -> None:
        """Async turn action

        :param method: str: Call method
        :param state: str: Call state
        :param kwargs: Any: Any arguments
        """

        action = getattr(self, method)

        if action:
            await action()

            is_on: bool = state == STATE_ON

            self._updater.data[self.entity_description.key] = is_on
            self._attr_is_on = is_on
            self._change_icon(is_on)

            self.async_write_ha_state()

    def _change_icon(self, is_on: bool) -> None:
        """Change icon

        :param is_on: bool
        """

        icon_name: str = (
            f"{self.entity_description.key}_{STATE_ON if is_on else STATE_OFF}"
        )
        if icon_name in ICONS:
            self._attr_icon = ICONS[icon_name]
