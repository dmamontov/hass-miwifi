"""Integration helper."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store
from homeassistant.loader import async_get_integration
from homeassistant.util import slugify
from httpx import codes

from .const import DOMAIN, STORAGE_VERSION, DEFAULT_TIMEOUT
from .updater import LuciUpdater


def get_config_value(
    config_entry: config_entries.ConfigEntry | None, param: str, default=None
) -> Any:
    """Get current value for configuration parameter.

    :param config_entry: config_entries.ConfigEntry|None: config entry from Flow
    :param param: str: parameter name for getting value
    :param default: default value for parameter, defaults to None
    :return Any: parameter value, or default value or None
    """

    return (
        config_entry.options.get(param, config_entry.data.get(param, default))
        if config_entry is not None
        else default
    )


async def async_verify_access(
    hass: HomeAssistant, ip: str, password: str, timeout: int = DEFAULT_TIMEOUT
) -> codes:
    """Verify ip and password.

    :param hass: HomeAssistant: Home Assistant object
    :param ip: str: device ip address
    :param password: str: device password
    :param timeout: int: Timeout
    :return int: last update success
    """

    updater = LuciUpdater(
        hass=hass, ip=ip, password=password, timeout=timeout, is_only_login=True
    )

    await updater.async_request_refresh()
    await updater.async_stop()

    return updater.code


async def async_user_documentation_url(hass: HomeAssistant) -> str:
    """Get the documentation url for creating a local user.

    :param hass: HomeAssistant: Home Assistant object
    :return str: Documentation URL
    """

    integration = await async_get_integration(hass, DOMAIN)

    return f"{integration.documentation}"


def generate_entity_id(entity_id_format: str, mac: str, name: str | None = None) -> str:
    """Generate Entity ID

    :param entity_id_format: str: Format
    :param mac: str: Mac address
    :param name: str | None: Name
    :return str: Entity ID
    """

    return entity_id_format.format(
        slugify(
            "miwifi_{}{}".format(mac, f"_{name}" if name is not None else "").lower()
        )
    )


def get_store(hass: HomeAssistant, ip: str) -> Store:
    """Create Store

    :param hass: HomeAssistant: Home Assistant object
    :param ip: str: IP address
    :return Store: Store object
    """

    return Store(hass, STORAGE_VERSION, f"{DOMAIN}/{ip}.json", encoder=JSONEncoder)


def parse_last_activity(last_activity: str) -> datetime:
    """Parse last activity string

    :param last_activity: str: Last activity
    :return datetime: Last activity in datetime
    """

    return datetime.strptime(last_activity, "%Y-%m-%dT%H:%M:%S")


def pretty_size(speed: float) -> str:
    """Convert up and down speed

    :param speed: float
    :return str: Speed
    """

    if speed == 0.0:
        return "0 B/s"

    unit = ("B/s", "KB/s", "MB/s", "GB/s")

    i = int(math.floor(math.log(speed, 1024)))
    p = math.pow(1024, i)
    s = round(speed / p, 2)

    return "%s %s" % (s, unit[i])
