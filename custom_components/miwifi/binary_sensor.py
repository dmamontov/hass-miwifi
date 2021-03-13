import logging

import homeassistant.helpers.device_registry as dr

from typing import Optional

from homeassistant.const import CONF_NAME, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.binary_sensor import ENTITY_ID_FORMAT, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import async_generate_entity_id

from .core.const import DATA_UPDATED, DOMAIN, BINARY_SENSORS
from .core.luci_data import LuciData

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities) -> None:
    luci = hass.data[DOMAIN][config_entry.entry_id]
    sensors = []

    for sensor, data in BINARY_SENSORS.items():
        if sensor in luci.api.data["binary_sensor"]:
            sensors.append(MiWiFiBinarySensor(hass, luci, sensor, data))

    async_add_entities(sensors, True)


class MiWiFiBinarySensor(BinarySensorEntity):
    def __init__(self, hass: HomeAssistant, luci: LuciData, code: str, data: dict) -> None:
        self.hass = hass
        self.luci = luci
        self.unsub_update = None

        self._code = code
        self._data = data
        self._state = False

        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT,
            "{}_{}".format(luci.api.device_data["name"], code),
            hass = hass
        )

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def unique_id(self) -> str:
        return self.entity_id

    @property
    def icon(self) -> str:
        return self._data["icon"]

    @property
    def available(self) -> bool:
        if "skip_available" in self._data and self._data["skip_available"]:
            return True

        return self.luci.available

    @property
    def device_info(self) -> dict:
        return {"connections": {(dr.CONNECTION_NETWORK_MAC, self.luci.api.device_data["mac"])}}

    @property
    def device_class(self) -> Optional[str]:
         return self._data["device_class"] if "device_class" in self._data else None

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
        try:
            self._state = self.luci.api.data["binary_sensor"][self._code]
        except KeyError:
            self._state = False
