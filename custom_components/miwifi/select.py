"""Select component."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.components.select import (
    ENTITY_ID_FORMAT,
    SelectEntityDescription,
    SelectEntity,
)
from homeassistant.config_entries import ConfigEntry
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
    ATTR_WIFI_2_4_DATA,
    ATTR_WIFI_5_0_DATA,
    ATTR_WIFI_5_0_GAME,
    ATTR_WIFI_ADAPTER_LENGTH,
    ATTR_SELECT_WIFI_2_4_CHANNEL,
    ATTR_SELECT_WIFI_2_4_CHANNELS,
    ATTR_SELECT_WIFI_2_4_CHANNEL_NAME,
    ATTR_SELECT_WIFI_5_0_CHANNEL,
    ATTR_SELECT_WIFI_5_0_CHANNEL_NAME,
    ATTR_SELECT_WIFI_5_0_CHANNELS,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNEL,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_NAME,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNELS,
)
from .enum import Wifi
from .helper import generate_entity_id
from .updater import LuciUpdater

KEY_MAP: Final = {
    ATTR_SELECT_WIFI_2_4_CHANNEL: ATTR_SELECT_WIFI_2_4_CHANNELS,
    ATTR_SELECT_WIFI_5_0_CHANNEL: ATTR_SELECT_WIFI_5_0_CHANNELS,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNEL: ATTR_SELECT_WIFI_5_0_GAME_CHANNELS,
}

DATA_MAP: Final = {
    ATTR_SELECT_WIFI_2_4_CHANNEL: ATTR_WIFI_2_4_DATA,
    ATTR_SELECT_WIFI_5_0_CHANNEL: ATTR_WIFI_5_0_DATA,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNEL: ATTR_WIFI_5_0_GAME,
}

MIWIFI_SELECTS: tuple[SelectEntityDescription, ...] = (
    SelectEntityDescription(
        key=ATTR_SELECT_WIFI_2_4_CHANNEL,
        name=ATTR_SELECT_WIFI_2_4_CHANNEL_NAME,
        icon="mdi:format-list-numbered",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SelectEntityDescription(
        key=ATTR_SELECT_WIFI_5_0_CHANNEL,
        name=ATTR_SELECT_WIFI_5_0_CHANNEL_NAME,
        icon="mdi:format-list-numbered",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SelectEntityDescription(
        key=ATTR_SELECT_WIFI_5_0_GAME_CHANNEL,
        name=ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_NAME,
        icon="mdi:format-list-numbered",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
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

    entities: list[MiWifiSelect] = []
    for description in MIWIFI_SELECTS:
        if (
            description.key == ATTR_SELECT_WIFI_5_0_GAME_CHANNEL
            and updater.data.get(ATTR_WIFI_ADAPTER_LENGTH, 2) != 3
        ):
            continue

        entities.append(
            MiWifiSelect(
                f"{config_entry.entry_id}-{description.key}",
                description,
                updater,
            )
        )

    async_add_entities(entities)


class MiWifiSelect(SelectEntity, CoordinatorEntity, RestoreEntity):
    """MiWifi select entry."""

    _attr_attribution: str = ATTRIBUTION

    def __init__(
        self,
        unique_id: str,
        description: SelectEntityDescription,
        updater: LuciUpdater,
    ) -> None:
        """Initialize switch.

        :param unique_id: str: Unique ID
        :param description: SelectEntityDescription: SelectEntityDescription object
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

        self._attr_current_option = updater.data.get(description.key, None)
        self._attr_options = updater.data.get(KEY_MAP[description.key], [])
        self._wifi_data = updater.data.get(DATA_MAP[description.key], {})

        self._attr_available = len(self._attr_options) > 0

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""

        await RestoreEntity.async_added_to_hass(self)
        await CoordinatorEntity.async_added_to_hass(self)

        state = await self.async_get_last_state()
        if not state:
            return

        self._attr_current_option = state.state

        self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        current_option: str = self._updater.data.get(self.entity_description.key, False)

        wifi_data: dict = self._updater.data.get(
            DATA_MAP[self.entity_description.key], {}
        )

        # fmt: off
        is_available: bool = self._updater.data.get(ATTR_STATE, False) \
            and len(self._attr_options) > 0 \
            and len(wifi_data) > 0
        # fmt: on

        is_update_data: bool = False
        for key, value in wifi_data.items():
            if key not in self._wifi_data or value != self._wifi_data[key]:
                is_update_data = True

                break

        if (
            self._attr_current_option == current_option
            and self._attr_available == is_available
            and not is_update_data
        ):
            return

        self._attr_available = is_available
        self._attr_current_option = current_option
        self._wifi_data = wifi_data

        self.async_write_ha_state()

    async def _wifi_2_4_channel_change(self, option: str) -> None:
        """Wifi 2.4G change option

        :param option: str: Option value
        """

        data: dict = {"wifiIndex": Wifi.ADAPTER_2_4.value, "channel": option}

        await self._async_update_wifi_adapter(data)

    async def _wifi_5_0_channel_change(self, option: str) -> None:
        """Wifi 5G change option

        :param option: str: Option value
        """

        data: dict = {"wifiIndex": Wifi.ADAPTER_5_0.value, "channel": option}

        await self._async_update_wifi_adapter(data)

    async def _wifi_5_0_game_channel_change(self, option: str) -> None:
        """Wifi 5G Game change option

        :param option: str: Option value
        """

        data: dict = {"wifiIndex": Wifi.ADAPTER_5_0_GAME.value, "channel": option}

        await self._async_update_wifi_adapter(data)

    async def _async_update_wifi_adapter(self, data: dict) -> None:
        """Update wifi adapter

        :param data: dict: Adapter data
        """

        try:
            await self._updater.luci.set_wifi(self._wifi_data | data)
        except BaseException as e:
            _LOGGER.debug("WiFi update error: %r", e)

            pass

    async def async_select_option(self, option: str) -> None:
        """Select option

        :param option: str: Option
        """

        if option not in self._attr_options:
            return

        action = getattr(self, f"_{self.entity_description.key}_change")

        if action:
            await action(option)

            self._updater.data[self.entity_description.key] = option
