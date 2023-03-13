"""Select component."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.components.select import (
    ENTITY_ID_FORMAT,
    SelectEntity,
    SelectEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_SELECT_SIGNAL_STRENGTH_OPTIONS,
    ATTR_SELECT_WIFI_2_4_CHANNEL,
    ATTR_SELECT_WIFI_2_4_CHANNEL_NAME,
    ATTR_SELECT_WIFI_2_4_CHANNEL_OPTIONS,
    ATTR_SELECT_WIFI_2_4_CHANNELS,
    ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH,
    ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH_NAME,
    ATTR_SELECT_WIFI_5_0_CHANNEL,
    ATTR_SELECT_WIFI_5_0_CHANNEL_NAME,
    ATTR_SELECT_WIFI_5_0_CHANNEL_OPTIONS,
    ATTR_SELECT_WIFI_5_0_CHANNELS,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNEL,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_NAME,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_OPTIONS,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNELS,
    ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH,
    ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH_NAME,
    ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH,
    ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH_NAME,
    ATTR_STATE,
    ATTR_WIFI_2_4_DATA,
    ATTR_WIFI_5_0_DATA,
    ATTR_WIFI_5_0_GAME_DATA,
    ATTR_WIFI_ADAPTER_LENGTH,
)
from .entity import MiWifiEntity
from .enum import Wifi, DeviceClass
from .exceptions import LuciError
from .updater import LuciUpdater, async_get_updater

PARALLEL_UPDATES = 0

CHANNELS_MAP: Final = {
    ATTR_SELECT_WIFI_2_4_CHANNEL: ATTR_SELECT_WIFI_2_4_CHANNELS,
    ATTR_SELECT_WIFI_5_0_CHANNEL: ATTR_SELECT_WIFI_5_0_CHANNELS,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNEL: ATTR_SELECT_WIFI_5_0_GAME_CHANNELS,
}

DATA_MAP: Final = {
    ATTR_SELECT_WIFI_2_4_CHANNEL: ATTR_WIFI_2_4_DATA,
    ATTR_SELECT_WIFI_5_0_CHANNEL: ATTR_WIFI_5_0_DATA,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNEL: ATTR_WIFI_5_0_GAME_DATA,
    ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH: ATTR_WIFI_2_4_DATA,
    ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH: ATTR_WIFI_5_0_DATA,
    ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH: ATTR_WIFI_5_0_GAME_DATA,
}

OPTIONS_MAP: Final = {
    ATTR_SELECT_WIFI_2_4_CHANNEL: ATTR_SELECT_WIFI_2_4_CHANNEL_OPTIONS,
    ATTR_SELECT_WIFI_5_0_CHANNEL: ATTR_SELECT_WIFI_5_0_CHANNEL_OPTIONS,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNEL: ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_OPTIONS,
    ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH: ATTR_SELECT_SIGNAL_STRENGTH_OPTIONS,
    ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH: ATTR_SELECT_SIGNAL_STRENGTH_OPTIONS,
    ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH: ATTR_SELECT_SIGNAL_STRENGTH_OPTIONS,
}

ICONS: Final = {
    f"{ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH}_min": "mdi:wifi-strength-1",
    f"{ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH}_mid": "mdi:wifi-strength-2",
    f"{ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH}_max": "mdi:wifi-strength-4",
    f"{ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH}_min": "mdi:wifi-strength-1",
    f"{ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH}_mid": "mdi:wifi-strength-2",
    f"{ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH}_max": "mdi:wifi-strength-4",
    f"{ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH}_min": "mdi:wifi-strength-1",
    f"{ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH}_mid": "mdi:wifi-strength-2",
    f"{ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH}_max": "mdi:wifi-strength-4",
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
    SelectEntityDescription(
        key=ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH,
        name=ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH_NAME,
        icon=ICONS[f"{ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH}_max"],
        device_class=DeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SelectEntityDescription(
        key=ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH,
        name=ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH_NAME,
        icon=ICONS[f"{ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH}_max"],
        device_class=DeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SelectEntityDescription(
        key=ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH,
        name=ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH_NAME,
        icon=ICONS[f"{ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH}_max"],
        device_class=DeviceClass.SIGNAL_STRENGTH,
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

    updater: LuciUpdater = async_get_updater(hass, config_entry.entry_id)

    entities: list[MiWifiSelect] = [
        MiWifiSelect(
            f"{config_entry.entry_id}-{description.key}",
            description,
            updater,
        )
        for description in MIWIFI_SELECTS
        if description.key
        not in [
            ATTR_SELECT_WIFI_5_0_GAME_CHANNEL,
            ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH,
        ]
        or updater.supports_game
    ]

    async_add_entities(entities)


class MiWifiSelect(MiWifiEntity, SelectEntity):
    """MiWifi select entry."""

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

        MiWifiEntity.__init__(self, unique_id, description, updater, ENTITY_ID_FORMAT)

        self._attr_current_option = updater.data.get(description.key, None)
        self._change_icon(self._attr_current_option)

        self._attr_options = []
        if description.key in CHANNELS_MAP:
            self._attr_options = updater.data.get(CHANNELS_MAP[description.key], [])

        if description.key in OPTIONS_MAP and len(self._attr_options) == 0:
            if (
                updater.data.get(ATTR_WIFI_ADAPTER_LENGTH, 2) > 2
                and description.key == ATTR_SELECT_WIFI_5_0_CHANNEL
            ):
                self._attr_options = [
                    option
                    for option in OPTIONS_MAP[description.key]
                    if option not in OPTIONS_MAP[ATTR_SELECT_WIFI_5_0_GAME_CHANNEL]
                ]
            else:
                self._attr_options = OPTIONS_MAP[description.key]

        self._wifi_data: dict = {}
        if description.key in DATA_MAP:
            self._wifi_data = updater.data.get(DATA_MAP[description.key], {})

        self._attr_available: bool = (
            updater.data.get(ATTR_STATE, False) and len(self._attr_options) > 0
        )

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        current_option: str = self._updater.data.get(self.entity_description.key, False)

        wifi_data: dict = {}
        if self.entity_description.key in DATA_MAP:
            wifi_data = self._updater.data.get(
                DATA_MAP[self.entity_description.key], {}
            )

        is_available: bool = (
            self._updater.data.get(ATTR_STATE, False)
            and len(self._attr_options) > 0
            and len(wifi_data) > 0
        )

        data_changed: list = [
            key
            for key, value in wifi_data.items()
            if key not in self._wifi_data or value != self._wifi_data[key]
        ]

        if (
            self._attr_current_option == current_option
            and self._attr_available == is_available
            and not data_changed
        ):
            return

        self._attr_available = is_available
        self._attr_current_option = current_option
        self._wifi_data = wifi_data

        self._change_icon(current_option)

        self.async_write_ha_state()

    async def _wifi_2_4_channel_change(self, option: str) -> None:
        """Wifi 2.4G change channel

        :param option: str: Option value
        """

        data: dict = {"wifiIndex": Wifi.ADAPTER_2_4.value, "channel": option}

        await self._async_update_wifi_adapter(data)

    async def _wifi_5_0_channel_change(self, option: str) -> None:
        """Wifi 5G change channel

        :param option: str: Option value
        """

        data: dict = {"wifiIndex": Wifi.ADAPTER_5_0.value, "channel": option}

        await self._async_update_wifi_adapter(data)

    async def _wifi_5_0_game_channel_change(self, option: str) -> None:
        """Wifi 5G Game change channel

        :param option: str: Option value
        """

        data: dict = {"wifiIndex": Wifi.ADAPTER_5_0_GAME.value, "channel": option}

        await self._async_update_wifi_adapter(data)

    async def _wifi_2_4_signal_strength_change(self, option: str) -> None:
        """Wifi 2.4G change signal strength

        :param option: str: Option value
        """

        data: dict = {"wifiIndex": Wifi.ADAPTER_2_4.value, "txpwr": option}

        await self._async_update_wifi_adapter(data)

    async def _wifi_5_0_signal_strength_change(self, option: str) -> None:
        """Wifi 5G change signal strength

        :param option: str: Option value
        """

        data: dict = {"wifiIndex": Wifi.ADAPTER_5_0.value, "txpwr": option}

        await self._async_update_wifi_adapter(data)

    async def _wifi_5_0_game_signal_strength_change(self, option: str) -> None:
        """Wifi 5G Game change signal strength

        :param option: str: Option value
        """

        data: dict = {"wifiIndex": Wifi.ADAPTER_5_0_GAME.value, "txpwr": option}

        await self._async_update_wifi_adapter(data)

    async def _async_update_wifi_adapter(self, data: dict) -> None:
        """Update wifi adapter

        :param data: dict: Adapter data
        """

        new_data: dict = self._wifi_data | data

        try:
            await self._updater.luci.set_wifi(new_data)
            self._wifi_data = new_data
        except LuciError as _e:
            _LOGGER.debug("WiFi update error: %r", _e)

    async def async_select_option(self, option: str) -> None:
        """Select option

        :param option: str: Option
        """

        if action := getattr(self, f"_{self.entity_description.key}_change"):
            await action(option)

            self._updater.data[self.entity_description.key] = option
            self._attr_current_option = option
            self._change_icon(option)

            self.async_write_ha_state()

    def _change_icon(self, option: str) -> None:
        """Change icon

        :param option: str
        """

        icon_name: str = f"{self.entity_description.key}_{option}"
        if icon_name in ICONS:
            self._attr_icon = ICONS[icon_name]
