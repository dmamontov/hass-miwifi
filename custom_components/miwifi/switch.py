"""Switch component."""

from __future__ import annotations

import logging
from typing import Any, Final

from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_BINARY_SENSOR_DUAL_BAND,
    ATTR_STATE,
    ATTR_SWITCH_WIFI_2_4,
    ATTR_SWITCH_WIFI_2_4_NAME,
    ATTR_SWITCH_WIFI_5_0,
    ATTR_SWITCH_WIFI_5_0_GAME,
    ATTR_SWITCH_WIFI_5_0_GAME_NAME,
    ATTR_SWITCH_WIFI_5_0_NAME,
    ATTR_SWITCH_WIFI_GUEST,
    ATTR_SWITCH_WIFI_GUEST_NAME,
    ATTR_WIFI_2_4_DATA,
    ATTR_WIFI_5_0_DATA,
    ATTR_WIFI_5_0_GAME_DATA,
    ATTR_WIFI_GUEST_DATA,
)
from .entity import MiWifiEntity
from .enum import Wifi
from .exceptions import LuciError
from .updater import LuciUpdater, async_get_updater

PARALLEL_UPDATES = 0

DATA_MAP: Final = {
    ATTR_SWITCH_WIFI_2_4: ATTR_WIFI_2_4_DATA,
    ATTR_SWITCH_WIFI_5_0: ATTR_WIFI_5_0_DATA,
    ATTR_SWITCH_WIFI_5_0_GAME: ATTR_WIFI_5_0_GAME_DATA,
    ATTR_SWITCH_WIFI_GUEST: ATTR_WIFI_GUEST_DATA,
}

ICONS: Final = {
    f"{ATTR_SWITCH_WIFI_2_4}_{STATE_ON}": "mdi:wifi",
    f"{ATTR_SWITCH_WIFI_2_4}_{STATE_OFF}": "mdi:wifi-off",
    f"{ATTR_SWITCH_WIFI_5_0}_{STATE_ON}": "mdi:wifi",
    f"{ATTR_SWITCH_WIFI_5_0}_{STATE_OFF}": "mdi:wifi-off",
    f"{ATTR_SWITCH_WIFI_5_0_GAME}_{STATE_ON}": "mdi:wifi",
    f"{ATTR_SWITCH_WIFI_5_0_GAME}_{STATE_OFF}": "mdi:wifi-off",
    f"{ATTR_SWITCH_WIFI_GUEST}_{STATE_ON}": "mdi:wifi-lock-open",
    f"{ATTR_SWITCH_WIFI_GUEST}_{STATE_OFF}": "mdi:wifi-off",
}

MIWIFI_SWITCHES: tuple[SwitchEntityDescription, ...] = (
    SwitchEntityDescription(
        key=ATTR_SWITCH_WIFI_2_4,
        name=ATTR_SWITCH_WIFI_2_4_NAME,
        icon=ICONS[f"{ATTR_SWITCH_WIFI_2_4}_{STATE_ON}"],
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=True,
    ),
    SwitchEntityDescription(
        key=ATTR_SWITCH_WIFI_5_0,
        name=ATTR_SWITCH_WIFI_5_0_NAME,
        icon=ICONS[f"{ATTR_SWITCH_WIFI_5_0}_{STATE_ON}"],
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=True,
    ),
    SwitchEntityDescription(
        key=ATTR_SWITCH_WIFI_5_0_GAME,
        name=ATTR_SWITCH_WIFI_5_0_GAME_NAME,
        icon=ICONS[f"{ATTR_SWITCH_WIFI_5_0_GAME}_{STATE_ON}"],
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=True,
    ),
    SwitchEntityDescription(
        key=ATTR_SWITCH_WIFI_GUEST,
        name=ATTR_SWITCH_WIFI_GUEST_NAME,
        icon=ICONS[f"{ATTR_SWITCH_WIFI_GUEST}_{STATE_ON}"],
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

    entities: list[MiWifiSwitch] = []
    for description in MIWIFI_SWITCHES:
        if description.key == ATTR_SWITCH_WIFI_5_0_GAME and not updater.supports_game:
            continue

        if description.key == ATTR_SWITCH_WIFI_GUEST and not updater.supports_guest:
            continue

        entities.append(
            MiWifiSwitch(
                f"{config_entry.entry_id}-{description.key}",
                description,
                updater,
            )
        )

    async_add_entities(entities)


class MiWifiSwitch(MiWifiEntity, SwitchEntity):
    """MiWifi switch entry."""

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

        MiWifiEntity.__init__(self, unique_id, description, updater, ENTITY_ID_FORMAT)

        self._attr_is_on = updater.data.get(description.key, False)
        self._change_icon(self._attr_is_on)

        self._attr_available = self._additional_prepare()

        self._wifi_data: dict = {}
        if description.key in DATA_MAP:
            self._wifi_data = updater.data.get(DATA_MAP[description.key], {})

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        is_on: bool = self._updater.data.get(self.entity_description.key, False)

        wifi_data: dict = {}
        if self.entity_description.key in DATA_MAP:
            wifi_data = self._updater.data.get(
                DATA_MAP[self.entity_description.key], {}
            )

        is_available: bool = self._additional_prepare() and len(wifi_data) > 0

        data_changed: list = [
            key
            for key, value in wifi_data.items()
            if key not in self._wifi_data or value != self._wifi_data[key]
        ]

        if (
            self._attr_is_on == is_on
            and self._attr_available == is_available
            and not data_changed
        ):
            return

        self._attr_available = is_available
        self._attr_is_on = is_on
        self._wifi_data = wifi_data

        self._change_icon(is_on)

        self.async_write_ha_state()

    async def _wifi_2_4_on(self) -> None:
        """Wifi 2.4G on action"""

        data: dict = {"wifiIndex": Wifi.ADAPTER_2_4.value, "on": 1}

        await self._async_update_wifi_adapter(data)

    async def _wifi_2_4_off(self) -> None:
        """Wifi 2.4G off action"""

        data: dict = {"wifiIndex": Wifi.ADAPTER_2_4.value, "on": 0}

        await self._async_update_wifi_adapter(data)

    async def _wifi_5_0_on(self) -> None:
        """Wifi 5G on action"""

        data: dict = {"wifiIndex": Wifi.ADAPTER_5_0.value, "on": 1}

        await self._async_update_wifi_adapter(data)

    async def _wifi_5_0_off(self) -> None:
        """Wifi 5G off action"""

        data: dict = {"wifiIndex": Wifi.ADAPTER_5_0.value, "on": 0}

        await self._async_update_wifi_adapter(data)

    async def _wifi_5_0_game_on(self) -> None:
        """Wifi 5G Game on action"""

        data: dict = {"wifiIndex": Wifi.ADAPTER_5_0_GAME.value, "on": 1}

        await self._async_update_wifi_adapter(data)

    async def _wifi_5_0_game_off(self) -> None:
        """Wifi 5G game off action"""

        data: dict = {"wifiIndex": Wifi.ADAPTER_5_0_GAME.value, "on": 0}

        await self._async_update_wifi_adapter(data)

    async def _wifi_guest_on(self) -> None:
        """Wifi 2.4G on action"""

        data: dict = {"wifiIndex": 3, "on": 1}

        await self._async_update_guest_wifi(data)

    async def _wifi_guest_off(self) -> None:
        """Wifi 2.4G off action"""

        data: dict = {"wifiIndex": 3, "on": 0}

        await self._async_update_guest_wifi(data)

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

    async def _async_update_guest_wifi(self, data: dict) -> None:
        """Update guest wifi

        :param data: dict: Guest data
        """

        new_data: dict = self._wifi_data | data

        try:
            await self._updater.luci.set_guest_wifi(new_data)
            self._wifi_data = new_data
        except LuciError as _e:
            _LOGGER.debug("WiFi update error: %r", _e)

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

        if action := getattr(self, method):
            await action()

            is_on: bool = state == STATE_ON

            self._updater.data[self.entity_description.key] = is_on
            self._attr_is_on = is_on
            self._change_icon(is_on)

            self.async_write_ha_state()

    def _additional_prepare(self) -> bool:
        """Prepare wifi switch

        return bool: is_available
        """

        is_available: bool = self._updater.data.get(ATTR_STATE, False)

        if self._updater.data.get(
            ATTR_BINARY_SENSOR_DUAL_BAND, False
        ) and self.entity_description.key in [
            ATTR_SWITCH_WIFI_5_0,
            ATTR_SWITCH_WIFI_5_0_GAME,
        ]:
            self._attr_entity_registry_enabled_default = False
            is_available = False

        return is_available and self.entity_description.key in self._updater.data

    def _change_icon(self, is_on: bool) -> None:
        """Change icon

        :param is_on: bool
        """

        icon_name: str = (
            f"{self.entity_description.key}_{STATE_ON if is_on else STATE_OFF}"
        )
        if icon_name in ICONS:
            self._attr_icon = ICONS[icon_name]
