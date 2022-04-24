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
    ATTR_BINARY_SENSOR_DUAL_BAND,
    ATTR_WIFI_NAME,
    ATTR_WIFI_ADAPTER_LENGTH,
    ATTR_SWITCH_WIFI_2_4,
    ATTR_SWITCH_WIFI_2_4_NAME,
    ATTR_WIFI_2_4_DATA,
    ATTR_SWITCH_WIFI_5_0,
    ATTR_SWITCH_WIFI_5_0_NAME,
    ATTR_WIFI_5_0_DATA,
    ATTR_SWITCH_WIFI_5_0_GAME,
    ATTR_SWITCH_WIFI_5_0_GAME_NAME,
    ATTR_WIFI_5_0_GAME_DATA,
    ATTR_SWITCH_WIFI_GUEST,
    ATTR_SWITCH_WIFI_GUEST_NAME,
    ATTR_WIFI_GUEST_DATA,
)
from .enum import Wifi
from .exceptions import LuciException
from .helper import generate_entity_id
from .updater import LuciUpdater

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

    data: dict = hass.data[DOMAIN][config_entry.entry_id]
    updater: LuciUpdater = data[UPDATER]

    if not updater.last_update_success:
        _LOGGER.error("Failed to initialize switch.")

        return

    entities: list[MiWifiSwitch] = []
    for description in MIWIFI_SWITCHES:
        if (
            description.key == ATTR_SWITCH_WIFI_5_0_GAME
            and updater.data.get(ATTR_WIFI_ADAPTER_LENGTH, 2) != 3
        ) or (
            description.key == ATTR_SWITCH_WIFI_GUEST
            and not updater.is_support_guest_wifi
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
        self._change_icon(self._attr_is_on)

        self._attr_available = self._additional_prepare()

        if description.key in DATA_MAP:
            self._wifi_data = updater.data.get(DATA_MAP[description.key], {})
        else:
            self._wifi_data = {}

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

        if self.entity_description.key in DATA_MAP:
            wifi_data: dict = self._updater.data.get(
                DATA_MAP[self.entity_description.key], {}
            )
        else:
            wifi_data = {}

        # fmt: off
        is_available: bool = self._additional_prepare() \
            and len(wifi_data) > 0
        # fmt: on

        is_update_data: bool = False
        for key, value in wifi_data.items():
            if key not in self._wifi_data or value != self._wifi_data[key]:
                is_update_data = True

                break

        if (
            self._attr_is_on == is_on
            and self._attr_available == is_available
            and not is_update_data
        ):
            return

        self._attr_available = is_available
        self._attr_is_on = is_on
        self._wifi_data = wifi_data

        self._change_icon(is_on)

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Is available

        :return bool: Is available
        """

        return self._attr_available and self.coordinator.last_update_success

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
        except LuciException as _e:
            _LOGGER.debug("WiFi update error: %r", _e)

    async def _async_update_guest_wifi(self, data: dict) -> None:
        """Update guest wifi

        :param data: dict: Guest data
        """

        new_data: dict = self._wifi_data | data

        try:
            await self._updater.luci.set_guest_wifi(new_data)
            self._wifi_data = new_data
        except LuciException as _e:
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

        action = getattr(self, method)

        if action:
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

    def _change_icon(self, is_on: bool) -> None:
        """Change icon

        :param is_on: bool
        """

        # fmt: off
        icon_name: str = f"{self.entity_description.key}_{STATE_ON if is_on else STATE_OFF}"
        # fmt: on
        if icon_name in ICONS:
            self._attr_icon = ICONS[icon_name]
