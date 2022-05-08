"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch
import pytest
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.miwifi.const import DOMAIN, UPDATER
from custom_components.miwifi.updater import LuciUpdater

from tests.setup import async_mock_luci_client, async_setup

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_init(hass: HomeAssistant) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_dispatcher_send"
    ), patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ), patch(
        "custom_components.miwifi.helper.Store"
    ) as mock_store:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        mock_store.return_value.async_load = AsyncMock(return_value=None)
        mock_store.return_value.async_save = AsyncMock(return_value=None)
        mock_store.return_value.async_remove = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success
        assert len(mock_store.mock_calls) == 3

        mock_store.reset_mock()

        await hass.config_entries.async_get_entry(config_entry.entry_id).async_remove(
            hass
        )
        await hass.async_block_till_done()

        assert len(mock_store.mock_calls) == 1
