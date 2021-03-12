import logging

import asyncio
import homeassistant.helpers.device_registry as dr

from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_PASSWORD
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from . import exceptions
from .const import (
    DOMAIN,
    DOMAINS,
    DATA_UPDATED,
    DEVICES_UPDATED,
    SCAN_INTERVAL,
    CONF_FORCE_LOAD_REPEATER_DEVICES,
    CONF_LAST_ACTIVITY_DAYS,
    DEFAULT_LAST_ACTIVITY_DAYS
)
from .luci import Luci

_LOGGER = logging.getLogger(__name__)

class LuciData:
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, store: Store, devices: dict):
        self.hass = hass
        self.config_entry = config_entry
        self.store = store

        session = async_get_clientsession(hass, False)

        self.api = Luci(
            hass,
            session,
            self.ip,
            self.password,
            {
                "is_force_load": config_entry.options.get(CONF_FORCE_LOAD_REPEATER_DEVICES, False)
            }
        )

        self.unsub_timer = None
        self.available = False
        self.re_auth = False

        self._devices = devices

    @property
    def ip(self):
        return self.config_entry.options[CONF_IP_ADDRESS]

    @property
    def password(self):
        return self.config_entry.options[CONF_PASSWORD]

    async def async_update(self):
        try:
            if self.re_auth:
                await self.api.login()

            await self.api.prepare_data()

            self.available = True
        except exceptions.LuciConnectionError:
            _LOGGER.debug("ERROR MiWifi connection error ({})".format(self.ip))
            self.re_auth = False
            self.available = False
        except exceptions.LuciTokenError:
            _LOGGER.debug("ERROR MiWifi token error ({})".format(self.ip))
            self.re_auth = True
            self.available = False

        _LOGGER.debug("MiWifi updated ({})".format(self.ip))

        self.api.set_state(self.available)

        if not self.api.is_repeater_mode:
            self.update_devices()

        async_dispatcher_send(self.hass, DATA_UPDATED)

        if self.available and self.re_auth:
            await self.update_device()
            self.re_auth = False

    def update_devices(self) -> None:
        async_dispatcher_send(self.hass, DEVICES_UPDATED)

    async def async_setup(self) -> bool:
        _LOGGER.debug("MiWiFi Async setup ({})".format(self.ip))

        try:
            await asyncio.sleep(1)

            await self.api.login()
            await self.api.prepare_data()

            self.available = True
        except Exception as e:
            _LOGGER.debug("MiWiFi Incorrect config ({}) %r".format(self.ip), e)
            raise ConfigEntryNotReady

        await self.update_device()

        self.api.set_state(self.available)

        if not self.api.is_repeater_mode:
            self.update_devices()

        self.set_scan_interval()
        self.config_entry.add_update_listener(self.async_options_updated)

        await self.check_last_activity()

        for domain in DOMAINS:
            self.hass.async_create_task(
                self.hass.config_entries.async_forward_entry_setup(self.config_entry, domain)
            )

        return True

    async def update_device(self):
        device_registry = await dr.async_get_registry(self.hass)
        device_registry.async_get_or_create(
            config_entry_id = self.config_entry.entry_id,
            connections = {(dr.CONNECTION_NETWORK_MAC, self.api.device_data["mac"])},
            identifiers = {(DOMAIN, self.api.device_data["mac"])},
            name = self.api.device_data["name"],
            manufacturer = self.api.device_data["manufacturer"],
            model = self.api.device_data["model"],
            sw_version = self.api.device_data["sw_version"],
        )

    def set_scan_interval(self):
        async def refresh(event_time):
            await self.async_update()
            await self.check_last_activity()
            await self.save_to_store()

        if self.unsub_timer is not None:
            self.unsub_timer()

        self.unsub_timer = async_track_time_interval(
            self.hass, refresh, timedelta(seconds = SCAN_INTERVAL)
        )

    @staticmethod
    async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry):
        hass.data[DOMAIN][entry.entry_id].set_scan_interval()

    async def check_last_activity(self) -> None:
        last_days = int(self.config_entry.options.get(CONF_LAST_ACTIVITY_DAYS, DEFAULT_LAST_ACTIVITY_DAYS))
        if last_days <= 0:
            return

        device_registry = await dr.async_get_registry(self.hass)
        now = datetime.now().replace(microsecond = 0)

        for mac in self._devices:
            last_activity = datetime.strptime(self._devices[mac]["last_activity"], "%Y-%m-%dT%H:%M:%S")
            if not last_activity:
                continue

            delta = now - last_activity

            if int(delta.days) > last_days:
                self.remove_device(mac)

                connections = dr._normalize_connections({(dr.CONNECTION_NETWORK_MAC, mac)})
                device = device_registry.async_get_device({(DOMAIN, mac)}, connections)
                if not device:
                    continue

                device_registry.async_remove_device(device.id)

    async def save_to_store(self) -> None:
        await self.store.async_save(self._devices)

    def add_device(self, mac: str, device: dict) -> None:
        add_device = device.copy()
        add_device["online"] = 0
        add_device["signal"] = 0

        self._devices[mac] = add_device

    def remove_device(self, mac: str) -> None:
        if mac in self._devices:
            del self._devices[mac]
