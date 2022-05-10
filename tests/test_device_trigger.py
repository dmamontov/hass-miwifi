"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines,line-too-long

from __future__ import annotations

import logging

import pytest
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import HomeAssistant

from custom_components.miwifi.const import DOMAIN, EVENT_TYPE_RESPONSE
from custom_components.miwifi.device_trigger import DEVICE, async_get_triggers

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_get_triggers(hass: HomeAssistant) -> None:
    """Get triggers test.

    :param hass: HomeAssistant
    """

    assert await async_get_triggers(hass, "test") == [
        {
            CONF_PLATFORM: DEVICE,
            CONF_DEVICE_ID: "test",
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: EVENT_TYPE_RESPONSE,
        }
    ]
