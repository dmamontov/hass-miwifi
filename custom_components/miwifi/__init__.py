"""MiWifi custom integration."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant, Event, CALLBACK_TYPE
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_IS_FORCE_LOAD,
    CONF_ACTIVITY_DAYS,
    OPTION_IS_FROM_FLOW,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_ACTIVITY_DAYS,
    DEFAULT_SLEEP,
    DEFAULT_CALL_DELAY,
    UPDATER,
    UPDATE_LISTENER,
    RELOAD_ENTRY,
)
from .discovery import async_start_discovery
from .helper import get_config_value, get_store
from .updater import LuciUpdater

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up entry configured via user interface.

    :param hass: HomeAssistant: Home Assistant object
    :param entry: ConfigEntry: Config Entry object
    :return bool: Is success
    """

    async_start_discovery(hass)

    is_new: bool = get_config_value(entry, OPTION_IS_FROM_FLOW, False)

    if is_new:
        hass.config_entries.async_update_entry(entry, data=entry.data, options={})

    ip: str = get_config_value(entry, CONF_IP_ADDRESS)

    updater: LuciUpdater = LuciUpdater(
        hass,
        ip,
        get_config_value(entry, CONF_PASSWORD),
        get_config_value(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        get_config_value(entry, CONF_TIMEOUT, DEFAULT_TIMEOUT),
        get_config_value(entry, CONF_IS_FORCE_LOAD, False),
        get_config_value(entry, CONF_ACTIVITY_DAYS, DEFAULT_ACTIVITY_DAYS),
        get_store(hass, ip),
    )

    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = {
        CONF_IP_ADDRESS: ip,
        UPDATER: updater,
        RELOAD_ENTRY: False,
    }

    hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER] = entry.add_update_listener(
        async_update_options
    )

    async def async_start(with_sleep: bool = False) -> None:
        """Async start.

        :param with_sleep: bool
        """

        await updater.update(True)

        if with_sleep:
            await asyncio.sleep(DEFAULT_SLEEP)

        hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    async def async_stop(event: Event) -> None:
        """Async stop

        :param event: Event: Home Assistant stop event
        """

        await updater.async_stop()

    if is_new:
        await async_start()
        await asyncio.sleep(DEFAULT_SLEEP)
    else:
        hass.loop.call_later(
            DEFAULT_CALL_DELAY,
            lambda: hass.async_create_task(async_start(True)),
        )

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_stop)

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options for entry that was configured via user interface.

    :param hass: HomeAssistant: Home Assistant object
    :param entry: ConfigEntry: Config Entry object
    """

    if entry.entry_id not in hass.data[DOMAIN]:
        return

    hass.data[DOMAIN][entry.entry_id][RELOAD_ENTRY] = True

    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove entry configured via user interface.

    :param hass: HomeAssistant: Home Assistant object
    :param entry: ConfigEntry: Config Entry object
    :return bool: Is success
    """

    if hass.data[DOMAIN][entry.entry_id].get(RELOAD_ENTRY, False):
        hass.data[DOMAIN][RELOAD_ENTRY] = False
    elif CONF_IP_ADDRESS in hass.data[DOMAIN][entry.entry_id]:
        store: Store = get_store(
            hass, hass.data[DOMAIN][entry.entry_id][CONF_IP_ADDRESS]
        )
        await store.async_remove()

    is_unload = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not is_unload:
        return is_unload

    update_listener: CALLBACK_TYPE = hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER]
    update_listener()
    hass.data[DOMAIN].pop(entry.entry_id)

    return is_unload
