import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_PASSWORD, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from .core.const import (
    DOMAIN,
    CONF_FORCE_LOAD_REPEATER_DEVICES,
    CONF_LAST_ACTIVITY_DAYS,
    DEFAULT_LAST_ACTIVITY_DAYS,
    STORAGE_VERSION
)
from .core.luci_data import LuciData

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(
        cv.ensure_list,
        [
            vol.Schema({
                vol.Required(CONF_IP_ADDRESS): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_FORCE_LOAD_REPEATER_DEVICES, default = False): cv.boolean,
                vol.Optional(CONF_LAST_ACTIVITY_DAYS, default = DEFAULT_LAST_ACTIVITY_DAYS): cv.positive_int,
            })
        ]
    )
}, extra = vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    success = True

    if DOMAIN not in config:
        return success

    for router in config[DOMAIN]:
        hass.data[DOMAIN][router[CONF_IP_ADDRESS]] = router

        hass.async_create_task(hass.config_entries.flow.async_init(
            DOMAIN, context = {'source': SOURCE_IMPORT}, data = router
        ))

    return success

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    if config_entry.data:
        hass.config_entries.async_update_entry(config_entry, data = {} , options = config_entry.data)

    store = Store(hass, STORAGE_VERSION, "{}.{}".format(DOMAIN, config_entry.entry_id), encoder = JSONEncoder)

    devices = await store.async_load()
    if devices is None:
        devices = {}

    client = LuciData(hass, config_entry, store, devices)

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = client

    async def async_close(event):
        await client.save_to_store()
        await client.api.logout()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_close)

    await _init_services(hass)

    if not await client.async_setup():
        return False

    return True

async def _init_services(hass: HomeAssistant):
    async def remove_devices(call: ServiceCall):
        data = dict(call.data)

        entity_to_mac = {}

        devices = data.pop('device_id', [])
        entities = data.pop('entity_id', None)

        entity_registry = await er.async_get_registry(hass)

        if entities:
            for entity_id in entities:
                entity = entity_registry.async_get(entity_id)
                if not entity:
                    continue

                devices.append(entity.device_id)

        if devices:
            device_registry = await dr.async_get_registry(hass)

            for device in devices:
                device_entry = device_registry.async_get(device)
                if not device_entry:
                    continue

                device_entities = er.async_entries_for_device(entity_registry, device, True)
                if device_entities:
                    for entity in device_entities:
                        entity_registry.async_remove(entity.entity_id)

                device_registry.async_remove_device(device)

                for entry in device_entry.config_entries:
                    if entry not in entity_to_mac:
                        entity_to_mac[entry] = []

                    for domain, mac in device_entry.identifiers:
                        entity_to_mac[entry].append(mac)

        if not entity_to_mac:
            return

        for entry_id in entity_to_mac:
            if entry_id not in hass.data[DOMAIN]:
                return

            for mac in entity_to_mac[entry_id]:
                hass.data[DOMAIN][entry_id].remove_device(mac)

    hass.services.async_register(DOMAIN, 'remove_devices', remove_devices)
