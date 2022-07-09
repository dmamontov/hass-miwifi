"""Integration helper."""

from __future__ import annotations

import math
import time
from datetime import datetime
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store
from homeassistant.loader import async_get_integration
from homeassistant.util import slugify
from httpx import codes

from .const import DEFAULT_TIMEOUT, DOMAIN, MANUFACTURERS, STORAGE_VERSION
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
    hass: HomeAssistant,
    ip: str,  # pylint: disable=invalid-name
    password: str,
    encryption: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> codes:
    """Verify ip and password.

    :param hass: HomeAssistant: Home Assistant object
    :param ip: str: device ip address
    :param encryption: str: password encryption
    :param password: str: device password
    :param timeout: int: Timeout
    :return int: last update success
    """

    updater = LuciUpdater(
        hass=hass,
        ip=ip,
        password=password,
        encryption=encryption,
        timeout=timeout,
        is_only_login=True,
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


async def async_get_version(hass: HomeAssistant) -> str:
    """Get the documentation url for creating a local user.

    :param hass: HomeAssistant: Home Assistant object
    :return str: Documentation URL
    """

    integration = await async_get_integration(hass, DOMAIN)

    return f"{integration.version}"


def generate_entity_id(entity_id_format: str, mac: str, name: str | None = None) -> str:
    """Generate Entity ID

    :param entity_id_format: str: Format
    :param mac: str: Mac address
    :param name: str | None: Name
    :return str: Entity ID
    """

    _name: str = f"_{name}" if name is not None else ""

    return entity_id_format.format(slugify(f"miwifi_{mac}{_name}".lower()))


def get_store(hass: HomeAssistant, ip: str) -> Store:  # pylint: disable=invalid-name
    """Create Store

    :param hass: HomeAssistant: Home Assistant object
    :param ip: str: IP address
    :return Store: Store object
    """

    return Store(hass, STORAGE_VERSION, f"{DOMAIN}/{ip}.json", encoder=JSONEncoder)


def parse_last_activity(last_activity: str) -> int:
    """Parse last activity string

    :param last_activity: str: Last activity
    :return int: Last activity in datetime
    """

    return int(
        time.mktime(datetime.strptime(last_activity, "%Y-%m-%dT%H:%M:%S").timetuple())
    )


def pretty_size(speed: float) -> str:
    """Convert up and down speed

    :param speed: float
    :return str: Speed
    """

    if speed == 0.0:
        return "0 B/s"

    _unit = ("B/s", "KB/s", "MB/s", "GB/s")

    _i = int(math.floor(math.log(speed, 1024)))
    _p = math.pow(1024, _i)

    return f"{round(speed / _p, 2)} {_unit[_i]}"


def detect_manufacturer(mac: str) -> str | None:
    """Get manufacturer by mac address

    :param mac: str: Mac address
    :return str | None: Manufacturer
    """

    identifier: str = mac.replace(":", "").upper()[:6]

    return MANUFACTURERS[identifier] if identifier in MANUFACTURERS else None
