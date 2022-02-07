import logging

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.device_registry as dr

from typing import Optional
from datetime import datetime, timedelta

from homeassistant.const import CONF_NAME, CONF_ICON, CONF_MAC, ATTR_GPS_ACCURACY, ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.components.device_tracker import SOURCE_TYPE_ROUTER
from homeassistant.components.device_tracker.config_entry import ScannerEntity, TrackerEntity
from homeassistant.config import load_yaml_config_file
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import UNDEFINED
from homeassistant.components.zone import ENTITY_ID_HOME

from .core.const import DEVICES_UPDATED, DOMAIN, DEVICE_TRACKER_ENTITY_ID_FORMAT, LEGACY_YAML_DEVICES
from .core.luci_data import LuciData
from .core.util import _generate_entity_id

_LOGGER = logging.getLogger(__name__)

legacy_schema = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_ICON, default = None): vol.Any(None, cv.icon),
        vol.Optional("track", default = False): cv.boolean,
        vol.Optional(CONF_MAC, default = None): vol.Any(
            None, vol.All(cv.string, vol.Upper)
        )
    }
)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities) -> None:
    luci = hass.data[DOMAIN][config_entry.entry_id]

    legacy_devices = await _get_legacy_devices(hass)

    zone_home = hass.states.get(ENTITY_ID_HOME)

    add_devices = []
    for mac in luci._devices:
        add_devices.append(
            MiWiFiDevice(hass, config_entry, luci, mac, luci._devices[mac], zone_home, False)
        )

    if add_devices:
        async_add_entities(add_devices)

    @callback
    def update_devices() -> None:
        if len(luci.api._new_devices) == 0:
            return

        new_devices = []
        for mac in luci.api._new_devices:
            if mac not in luci.api._devices_list or mac in luci._devices:
                continue

            new_device = _get_new_device(
                hass,
                luci.api._devices_list[mac],
                legacy_devices[mac] if mac in legacy_devices else {}
            )

            new_device["last_activity"] = datetime.now().replace(microsecond=0).isoformat()

            _LOGGER.info("New device {} ({}) from {}".format(new_device["name"], mac, luci.api._ip))

            new_devices.append(
                MiWiFiDevice(hass, config_entry, luci, mac, new_device, zone_home)
            )
            luci.add_device(mac, new_device)

        if new_devices:
            async_add_entities(new_devices)

    async_dispatcher_connect(
        hass, DEVICES_UPDATED, update_devices
    )

    update_devices()

def _get_new_device(hass: HomeAssistant, device: dict, legacy_device: dict) -> dict:
    return {
        "ip": device["ip"][0]["ip"] if "ip" in device else "0:0:0:0",
        "connection": device["connection"] if "connection" in device else "undefined",
        "router_mac": device["router_mac"],
        "name": legacy_device["name"] if "name" in legacy_device else device["name"],
        "icon": legacy_device["icon"] if "icon" in legacy_device else None,
        "signal": device["signal"],
        "online": device["ip"][0]["online"] if "ip" in device else "0",
        "unique_id": _generate_entity_id(
            DEVICE_TRACKER_ENTITY_ID_FORMAT,
            legacy_device["dev_id"] if "dev_id" in legacy_device else device["name"]
        )
    }

async def _get_legacy_devices(hass: HomeAssistant) -> dict:
    legacy_devices = {}

    try:
        devices = await hass.async_add_executor_job(load_yaml_config_file, hass.config.path(LEGACY_YAML_DEVICES))
    except HomeAssistantError:
        return {}
    except FileNotFoundError:
        return {}

    for dev_id, device in devices.items():
        try:
            device = legacy_schema(device)
            device["dev_id"] = cv.slugify(dev_id)
        except vol.Invalid:
            continue
        else:
            legacy_devices[device["mac"]] = dict(device)

    return legacy_devices

class MiWiFiDevice(ScannerEntity, TrackerEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        luci: LuciData,
        mac: str,
        device: dict,
        zone_home: Optional[State] = None,
        is_active: bool = True
    ) -> None:
        self.hass = hass
        self.luci = luci
        self.entity_id = device["unique_id"]

        self._config_entry = config_entry
        self._unsub_update = None

        self._mac = mac
        self._device = device
        self._name = device["name"]
        self._icon = device["icon"]
        self._active = is_active
        self._available = True

        self._attrs = {"scanner": DOMAIN}

        if zone_home:
            self._attrs[ATTR_LATITUDE] = zone_home.attributes[ATTR_LATITUDE]
            self._attrs[ATTR_LONGITUDE] = zone_home.attributes[ATTR_LONGITUDE]
            self._attrs[ATTR_GPS_ACCURACY] = 0

    @property
    def unique_id(self) -> str:
        return self.entity_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def icon(self) -> str:
        if self._icon:
            self._icon.replace("-android", "")

        return self._icon

    @property
    def is_connected(self):
        return self._active

    @property
    def source_type(self) -> str:
        return SOURCE_TYPE_ROUTER

    @property
    def ip_address(self) -> str:
        return self._device["ip"]

    @property
    def mac_address(self) -> str:
        return self._mac

    @property
    def available(self) -> bool:
        return self._available

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "mac": self._mac,
            "ip": self._device["ip"],
            "online": str(timedelta(seconds = int(self._device["online"]))),
            "connection": self._device["connection"],
            "router_mac": self._device["router_mac"],
            "signal": self._device["signal"],
            "last_activity": self._device["last_activity"],
        }

    @property
    def device_info(self) -> dict:
        return {
            'connections': {(dr.CONNECTION_NETWORK_MAC, self._mac)},
            'identifiers': {(DOMAIN, self._mac)},
            'name': self._name,
            'via_device': (DOMAIN, self._device["router_mac"])
        }

    @property
    def location_accuracy(self) -> Optional[int]:
        return self._attrs[ATTR_GPS_ACCURACY] if self._active and ATTR_GPS_ACCURACY in self._attrs else None

    @property
    def latitude(self) -> Optional[float]:
        return self._attrs[ATTR_LATITUDE] if self._active and ATTR_LATITUDE in self._attrs else None

    @property
    def longitude(self) -> Optional[float]:
        return self._attrs[ATTR_LONGITUDE] if self._active and ATTR_LONGITUDE in self._attrs else None

    @property
    def state_attributes(self) -> dict:
        return self._attrs if self._active else {"scanner": DOMAIN}

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self) -> None:
        self.unsub_update = async_dispatcher_connect(
            self.hass, DEVICES_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self) -> None:
        if self._update():
            self.async_schedule_update_ha_state(True)

    async def will_remove_from_hass(self) -> None:
        if self.unsub_update:
            self.unsub_update()

        self.unsub_update = None
        self.luci.remove_device(self._mac)

    async def async_removed_from_registry(self) -> None:
        self.luci.remove_device(self._mac)

    def _update(self) -> bool:
        is_changed = False
        is_active = False
        is_available = False
        is_available_all = False

        remove_enries = []
        for entry_id in dict(self.hass.data[DOMAIN]):
            if self.hass.data[DOMAIN][entry_id].available:
                is_available_all = True

            if self._mac in self.hass.data[DOMAIN][entry_id].api._current_devices:
                is_active = True

                old_device = self._device.copy()
                device = self.hass.data[DOMAIN][entry_id].api._devices_list[self._mac]

                if "ip" in device and len(device["ip"]) > 0:
                    self._device["ip"] = device["ip"][0]["ip"] if "ip" in device["ip"][0] else "127.0.0.1"
                    self._device["online"] = device["ip"][0]["online"] if "online" in device["ip"][0] else "0"
                else:
                    self._device["ip"] = "127.0.0.1"
                    self._device["online"] = "0"

                self._device["connection"] = device["connection"] if "connection" in device else "undefined"
                self._device["signal"] = device["signal"]
                self._device["router_mac"] = device["router_mac"]

                if old_device["router_mac"] != self._device["router_mac"]:
                    self.luci.remove_device(self._mac)
                    remove_enries.append(self._config_entry)

                    self.luci = self.hass.data[DOMAIN][entry_id]
                    self._config_entry = self.luci.config_entry

                is_available = self.hass.data[DOMAIN][entry_id].available

                for field in ["ip", "online", "connection", "signal", "router_mac"]:
                    if old_device[field] != self._device[field]:
                        is_changed = True
            else:
                remove_enries.append(self.hass.data[DOMAIN][entry_id].config_entry)

        if is_active:
            self._device["last_activity"] = datetime.now().replace(microsecond=0).isoformat()

            self.luci.add_device(self._mac, self._device)

            for entry in remove_enries:
                self._update_device(self._config_entry, entry)
        else:
            is_available = is_available_all
            if self._device["signal"] != 0 and self._device["online"] != 0:
                is_changed = True

            self._device["signal"] = 0
            self._device["online"] = 0

        if self._available != is_available or self._active != is_active:
            is_changed = True

        self._available = is_available
        self._active = is_active

        return is_changed

    def _update_device(self, new_entry: ConfigEntry, remove_entry: ConfigEntry) -> None:
        device_registry = dr.async_get(self.hass)

        connections = dr._normalize_connections({(dr.CONNECTION_NETWORK_MAC, self._mac)})
        device = device_registry.async_get_device({(DOMAIN, self._mac)}, connections)

        if not device:
            return

        via = device_registry.async_get_device({(DOMAIN, self._device["router_mac"])})

        device_registry.async_update_device(
            device.id,
            add_config_entry_id = new_entry.entry_id,
            remove_config_entry_id = remove_entry.entry_id,
            via_device_id = via.id if via else UNDEFINED,
            merge_connections = connections,
            merge_identifiers = {(DOMAIN, self._mac)},
            manufacturer = UNDEFINED,
            model = UNDEFINED,
            name = self._name,
            sw_version = UNDEFINED,
            entry_type = UNDEFINED,
            disabled_by = UNDEFINED,
        )
