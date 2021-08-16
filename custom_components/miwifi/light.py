import logging

import homeassistant.helpers.device_registry as dr

from homeassistant.core import HomeAssistant, callback
from homeassistant.components.light import ENTITY_ID_FORMAT, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .core.util import _generate_entity_id
from .core.const import DATA_UPDATED, DOMAIN, LIGHTS
from .core.luci_data import LuciData

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities) -> None:
    luci = hass.data[DOMAIN][config_entry.entry_id]
    lights = []

    for light, data in LIGHTS.items():
        lights.append(MiWiFiLight(hass, luci, light, data))

    async_add_entities(lights, True)

class MiWiFiLight(LightEntity):
    def __init__(self, hass: HomeAssistant, luci: LuciData, code: str, data: dict) -> None:
        self.hass = hass
        self.luci = luci
        self.unsub_update = None

        self._code = code
        self._data = data
        self._state = False
        self._is_block = False

        self.entity_id = _generate_entity_id(
            ENTITY_ID_FORMAT,
            "{}_{}".format(luci.api.device_data["name"], code)
        )

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def unique_id(self) -> str:
        return self.entity_id

    @property
    def icon(self) -> str:
        return self._data["icon_on"] if self._state else self._data["icon_off"]

    @property
    def available(self) -> bool:
        if "skip_available" in self._data and self._data["skip_available"]:
            return True

        return self.luci.available

    @property
    def device_info(self) -> dict:
        return {"connections": {(dr.CONNECTION_NETWORK_MAC, self.luci.api.device_data["mac"])}}

    @property
    def is_on(self) -> bool:
        return self._state

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self) -> None:
        self.unsub_update = async_dispatcher_connect(
            self.hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self) -> None:
        self.async_schedule_update_ha_state(True)

    async def will_remove_from_hass(self) -> None:
        if self.unsub_update:
            self.unsub_update()

        self.unsub_update = None

    async def async_update(self) -> None:
        if self._is_block:
            self._is_block = False

            return

        try:
            self._state = self.luci.api.data["light"][self._code]
        except KeyError:
            self._state = False

    async def led_on(self) -> None:
        try:
            await self.luci.api.led(1)
        except:
            self._state = True

        self._state = True

    async def led_off(self) -> None:
        try:
            await self.luci.api.led(0)
        except:
            self._state = False

        self._state = False

    async def async_turn_on(self, **kwargs) -> None:
        action = getattr(self, self._data["action_on"])

        await action()

        self.async_schedule_update_ha_state(True)
        self._is_block = True

    async def async_turn_off(self, **kwargs) -> None:
        action = getattr(self, self._data["action_off"])

        await action()

        self.async_schedule_update_ha_state(True)
        self._is_block = True
