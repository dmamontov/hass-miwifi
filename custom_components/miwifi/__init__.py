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
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant
from homeassistant.exceptions import PlatformNotReady

from .const import (
    CONF_ACTIVITY_DAYS,
    CONF_ENCRYPTION_ALGORITHM,
    CONF_IS_FORCE_LOAD,
    DEFAULT_ACTIVITY_DAYS,
    DEFAULT_CALL_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLEEP,
    DEFAULT_TIMEOUT,
    DOMAIN,
    OPTION_IS_FROM_FLOW,
    PLATFORMS,
    UPDATE_LISTENER,
    UPDATER,
)
from .discovery import async_start_discovery
from .enum import EncryptionAlgorithm
from .helper import get_config_value, get_store
from .services import SERVICES
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

    _ip: str = get_config_value(entry, CONF_IP_ADDRESS)

    _updater: LuciUpdater = LuciUpdater(
        hass,
        _ip,
        get_config_value(entry, CONF_PASSWORD),
        get_config_value(entry, CONF_ENCRYPTION_ALGORITHM, EncryptionAlgorithm.SHA1),
        get_config_value(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        get_config_value(entry, CONF_TIMEOUT, DEFAULT_TIMEOUT),
        get_config_value(entry, CONF_IS_FORCE_LOAD, False),
        get_config_value(entry, CONF_ACTIVITY_DAYS, DEFAULT_ACTIVITY_DAYS),
        get_store(hass, _ip),
        entry_id=entry.entry_id,
    )

    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = {
        CONF_IP_ADDRESS: _ip,
        UPDATER: _updater,
    }

    hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER] = entry.add_update_listener(
        async_update_options
    )

    async def async_start(with_sleep: bool = False) -> None:
        """Async start.

        :param with_sleep: bool
        """

        await _updater.async_config_entry_first_refresh()
        if not _updater.last_update_success:
            if _updater.last_exception is not None:
                raise PlatformNotReady from _updater.last_exception

            raise PlatformNotReady

        if with_sleep:
            await asyncio.sleep(DEFAULT_SLEEP)

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if is_new:
        await async_start()
        await asyncio.sleep(DEFAULT_SLEEP)
    else:
        hass.loop.call_later(
            DEFAULT_CALL_DELAY,
            lambda: hass.async_create_task(async_start(True)),
        )

    async def async_stop(event: Event) -> None:
        """Async stop"""

        await _updater.async_stop()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_stop)

    for service_name, service in SERVICES:
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(
                DOMAIN, service_name, service(hass).async_call_service, service.schema
            )

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options for entry that was configured via user interface.

    :param hass: HomeAssistant: Home Assistant object
    :param entry: ConfigEntry: Config Entry object
    """

    if entry.entry_id not in hass.data[DOMAIN]:
        return

    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove entry configured via user interface.

    :param hass: HomeAssistant: Home Assistant object
    :param entry: ConfigEntry: Config Entry object
    :return bool: Is success
    """

    if is_unload := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        _updater: LuciUpdater = hass.data[DOMAIN][entry.entry_id][UPDATER]
        await _updater.async_stop()

        _update_listener: CALLBACK_TYPE = hass.data[DOMAIN][entry.entry_id][
            UPDATE_LISTENER
        ]
        _update_listener()

        hass.data[DOMAIN].pop(entry.entry_id)

    return is_unload


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clear store on deletion.

    :param hass: HomeAssistant: Home Assistant object
    :param entry: ConfigEntry: Config Entry object
    """

    _updater: LuciUpdater = hass.data[DOMAIN][entry.entry_id][UPDATER]
    await _updater.async_stop(clean_store=True)
