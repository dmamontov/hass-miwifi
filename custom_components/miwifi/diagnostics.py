"""MiWifi diagnostic."""

from __future__ import annotations

from typing import Final

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ID,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant

from .updater import async_get_updater

TO_REDACT: Final = {
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_URL,
    CONF_TOKEN,
    CONF_ID,
    "routerId",
    "gateWay",
    "hostname",
    "ipv4",
    "ssid",
    "pwd",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""

    _data: dict = {"config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT)}

    if _updater := async_get_updater(hass, config_entry.entry_id):
        if hasattr(_updater, "data"):
            _data["data"] = async_redact_data(_updater.data, TO_REDACT)

        if hasattr(_updater, "devices"):
            _data["devices"] = _updater.devices

        if len(_updater.luci.diagnostics) > 0:
            _data["requests"] = async_redact_data(_updater.luci.diagnostics, TO_REDACT)

    return _data
