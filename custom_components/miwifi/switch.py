"""Switch component."""

from __future__ import annotations

import logging
from typing import Any, Final

from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    SwitchEntityDescription,
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ENTITY_CATEGORY_CONFIG,
    STATE_ON,
    STATE_OFF,
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
    ATTR_BINARY_SENSOR_DUAL_BAND,
    ATTR_WIFI_NAME,
    ATTR_WIFI_ADAPTER_LENGTH,
    ATTR_SWITCH_WIFI_2_4,
    ATTR_SWITCH_WIFI_2_4_NAME,
    ATTR_SWITCH_WIFI_5_0,
    ATTR_SWITCH_WIFI_5_0_NAME,
    ATTR_SWITCH_WIFI_5_0_GAME,
    ATTR_SWITCH_WIFI_5_0_GAME_NAME,
)
from .helper import generate_entity_id
from .updater import LuciUpdater

ICONS: Final = {
    f"{ATTR_SWITCH_WIFI_2_4}_{STATE_ON}": "mdi:wifi",
    f"{ATTR_SWITCH_WIFI_2_4}_{STATE_OFF}": "mdi:wifi-off",
    f"{ATTR_SWITCH_WIFI_5_0}_{STATE_ON}": "mdi:wifi",
    f"{ATTR_SWITCH_WIFI_5_0}_{STATE_OFF}": "mdi:wifi-off",
    f"{ATTR_SWITCH_WIFI_5_0_GAME}_{STATE_ON}": "mdi:wifi",
    f"{ATTR_SWITCH_WIFI_5_0_GAME}_{STATE_OFF}": "mdi:wifi-off",
}

MIWIFI_SWITCHES: tuple[SwitchEntityDescription, ...] = (
    SwitchEntityDescription(
        key=ATTR_SWITCH_WIFI_2_4,
        name=ATTR_SWITCH_WIFI_2_4_NAME,
        icon=ICONS[f"{ATTR_SWITCH_WIFI_2_4}_{STATE_ON}"],
        entity_category=ENTITY_CATEGORY_CONFIG,
        entity_registry_enabled_default=True,
    ),
    SwitchEntityDescription(
        key=ATTR_SWITCH_WIFI_5_0,
        name=ATTR_SWITCH_WIFI_5_0_NAME,
        icon=ICONS[f"{ATTR_SWITCH_WIFI_5_0}_{STATE_ON}"],
        entity_category=ENTITY_CATEGORY_CONFIG,
        entity_registry_enabled_default=True,
    ),
    SwitchEntityDescription(
        key=ATTR_SWITCH_WIFI_5_0_GAME,
        name=ATTR_SWITCH_WIFI_5_0_GAME_NAME,
        icon=ICONS[f"{ATTR_SWITCH_WIFI_5_0_GAME}_{STATE_ON}"],
        entity_category=ENTITY_CATEGORY_CONFIG,
        entity_registry_enabled_default=True,
    ),
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MiWifi switch entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: ConfigEntry object
    :param async_add_entities: AddEntitiesCallback: AddEntitiesCallback callback object
    """

    data: dict = hass.data[DOMAIN][config_entry.entry_id]
    updater: LuciUpdater = data[UPDATER]

    if not updater.data.get(ATTR_DEVICE_MAC_ADDRESS, False):
        _LOGGER.error("Failed to initialize switch: Missing mac address. Restart HASS.")

    entities: list[MiWifiSwitch] = []
    for description in MIWIFI_SWITCHES:
        if (
            description.key == ATTR_SWITCH_WIFI_5_0_GAME
            and updater.data.get(ATTR_WIFI_ADAPTER_LENGTH, 2) != 3
        ):
            continue

        entities.append(
            MiWifiSwitch(
                f"{config_entry.entry_id}-{description.key}",
                description,
                updater,
            )
        )

    async_add_entities(entities)


class MiWifiSwitch(SwitchEntity, CoordinatorEntity, RestoreEntity):
    """MiWifi switch entry."""

    _attr_attribution: str = ATTRIBUTION

    def __init__(
        self,
        unique_id: str,
        description: SwitchEntityDescription,
        updater: LuciUpdater,
    ) -> None:
        """Initialize switch.

        :param unique_id: str: Unique ID
        :param description: SwitchEntityDescription: SwitchEntityDescription object
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

        self._attr_is_on = updater.data.get(description.key, False)

        self._attr_available = self._additional_prepare()

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

        is_on: bool = self._updater.data.get(self.entity_description.key, False)

        is_available: bool = self._additional_prepare()

        if self._attr_is_on == is_on and self._attr_available == is_available:
            return

        self._attr_available = is_available
        self._attr_is_on = is_on

        icon_name: str = "{}_{}".format(
            self.entity_description.key, STATE_ON if is_on else STATE_OFF
        )

        if icon_name in ICONS:
            self._attr_icon = ICONS[icon_name]

        self.async_write_ha_state()

    async def _wifi_2_4_on(self, **kwargs: Any) -> None:
        """Wifi 2.4G on action

        :param kwargs: Any: Any arguments
        """

        await self._async_wifi_turn_on(1)

    async def _wifi_2_4_off(self, **kwargs: Any) -> None:
        """Wifi 2.4G off action

        :param kwargs: Any: Any arguments
        """

        await self._async_wifi_turn_off(2)

    async def _wifi_5_0_on(self, **kwargs: Any) -> None:
        """Wifi 5G on action

        :param kwargs: Any: Any arguments
        """

        await self._async_wifi_turn_on(2)

    async def _wifi_5_0_off(self, **kwargs: Any) -> None:
        """Wifi 5G off action

        :param kwargs: Any: Any arguments
        """

        await self._async_wifi_turn_off(2)

    async def _wifi_5_0_game_on(self, **kwargs: Any) -> None:
        """Wifi 5G Game on action

        :param kwargs: Any: Any arguments
        """

        await self._async_wifi_turn_on(3)

    async def _wifi_5_0_game_off(self, **kwargs: Any) -> None:
        """Wifi 5G game off action

        :param kwargs: Any: Any arguments
        """

        await self._async_wifi_turn_off(3)

    async def _async_wifi_turn_on(self, index: int) -> None:
        """Turn on wifi with index

        :param index: int: Wifi device index
        """

        try:
            await self._updater.luci.wifi_turn_on(index)
        except BaseException:
            pass

    async def _async_wifi_turn_off(self, index: int) -> None:
        """Turn off wifi with index

        :param index: int: Wifi device index
        """

        try:
            await self._updater.luci.wifi_turn_off(index)
        except BaseException:
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
            await action(**kwargs)

            self._updater.data[self.entity_description.key] = state == STATE_ON

    def _additional_prepare(self) -> bool:
        """Prepare wifi switch

        reuturn bool: is_available
        """

        is_available: bool = self._updater.data.get(ATTR_STATE, False)

        if self._updater.data.get(ATTR_BINARY_SENSOR_DUAL_BAND, False):
            if self.entity_description.key in [
                ATTR_SWITCH_WIFI_5_0,
                ATTR_SWITCH_WIFI_5_0_GAME,
            ]:
                self._attr_entity_registry_enabled_default = False
                is_available = False

            if self.entity_description.key == ATTR_SWITCH_WIFI_2_4:
                self._attr_name = ATTR_WIFI_NAME

        return is_available
