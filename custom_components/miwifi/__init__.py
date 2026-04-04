"""MiWifi custom integration."""

from __future__ import annotations

import asyncio
import logging
import traceback

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.components import persistent_notification
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant
from homeassistant.exceptions import PlatformNotReady

from .const import (
    CONF_ACTIVITY_DAYS,
    CONF_AUTO_DISCOVER,
    CONF_ENCRYPTION_ALGORITHM,
    CONF_IS_FORCE_LOAD,
    CONF_SETUP_TIMEOUT,
    DEFAULT_ACTIVITY_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SETUP_TIMEOUT,
    DEFAULT_SLEEP,
    DEFAULT_TIMEOUT,
    DOMAIN,
    OPTION_IS_FROM_FLOW,
    PLATFORMS,
    UPDATE_LISTENER,
    UPDATER,
)
from .discovery import async_is_discovery_enabled, async_start_discovery, async_stop_discovery
from .enum import EncryptionAlgorithm
from .helper import async_get_version, get_config_value, get_store
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

    _LOGGER.info(
        "Setting up MiWiFi integration version %s for entry %s",
        await async_get_version(hass),
        entry.entry_id,
    )

    notification_id: str = f"{DOMAIN}_{entry.entry_id}_setup_error"
    # Clear the previous setup error so a successful retry does not leave stale UI noise behind.
    persistent_notification.async_dismiss(hass, notification_id)

    is_new: bool = get_config_value(entry, OPTION_IS_FROM_FLOW, False)

    if is_new:
        hass.config_entries.async_update_entry(entry, data=entry.data, options={})

    _ip: str = get_config_value(entry, CONF_IP_ADDRESS)
    _setup_timeout: int = get_config_value(
        entry, CONF_SETUP_TIMEOUT, DEFAULT_SETUP_TIMEOUT
    )

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
        CONF_AUTO_DISCOVER: get_config_value(entry, CONF_AUTO_DISCOVER, True),
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

        # First refresh is allowed to run longer than normal polling because it discovers
        # capabilities, builds entities, and may need to walk mesh topology.
        _previous_timeout: int = _updater.luci.timeout
        _updater.luci.timeout = _setup_timeout
        try:
            await _updater.async_config_entry_first_refresh()
        finally:
            _updater.luci.timeout = _previous_timeout
        if not _updater.last_update_success:
            if _updater.last_exception is not None:
                raise PlatformNotReady from _updater.last_exception

            raise PlatformNotReady

        if with_sleep:
            # Reloads wait a moment before platform setup so the router can settle after
            # reauthentication and optional discovery work.
            await asyncio.sleep(DEFAULT_SLEEP)

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    try:
        # New entries start immediately so config-flow failures surface to the user. Reloads
        # keep the small delay inside async_start() because the entry already exists.
        if is_new:
            await async_start()
            await asyncio.sleep(DEFAULT_SLEEP)
        else:
            await async_start(True)
    except Exception as err:
        trace: str = "".join(
            traceback.format_exception(type(err), err, err.__traceback__)
        )

        _LOGGER.exception("Failed to set up MiWiFi entry %s", entry.entry_id)

        # Home Assistant often shows a generic setup failure in the UI. Keep the full
        # traceback available in a persistent notification so the first failed attempt is actionable.
        persistent_notification.async_create(
            hass,
            (
                f"MiWiFi setup failed for `{_ip}`.\n\n"
                f"Error: `{err}`\n\n"
                "<details><summary>Traceback</summary>\n\n"
                f"```python\n{trace}\n```\n"
                "</details>"
            ),
            title="MiWiFi setup failed",
            notification_id=notification_id,
        )

        raise

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

        if not async_is_discovery_enabled(hass):
            async_stop_discovery(hass)

    return is_unload


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clear store on deletion.

    :param hass: HomeAssistant: Home Assistant object
    :param entry: ConfigEntry: Config Entry object
    """

    await get_store(hass, get_config_value(entry, CONF_IP_ADDRESS)).async_remove()


