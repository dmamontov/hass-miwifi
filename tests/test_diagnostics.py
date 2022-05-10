"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture
from pytest_httpx import HTTPXMock

from custom_components.miwifi.const import DOMAIN, UPDATER
from custom_components.miwifi.diagnostics import (
    TO_REDACT,
    async_get_config_entry_diagnostics,
)
from custom_components.miwifi.updater import LuciUpdater
from tests.setup import async_setup, get_url

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_init(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        text=load_fixture("init_info_data.json"),
        method="GET",
        url=get_url("xqsystem/init_info"),
    )
    httpx_mock.add_response(
        text=load_fixture("status_data.json"),
        method="GET",
        url=get_url("misystem/status"),
    )
    httpx_mock.add_response(
        text=load_fixture("mode_data.json"),
        method="GET",
        url=get_url("xqnetwork/mode"),
    )
    httpx_mock.add_response(
        text=load_fixture("wifi_detail_all_data.json"),
        method="GET",
        url=get_url("xqnetwork/wifi_detail_all"),
    )
    httpx_mock.add_response(
        text=load_fixture("wifi_diag_detail_all_data.json"),
        method="GET",
        url=get_url("xqnetwork/wifi_diag_detail_all"),
    )
    httpx_mock.add_response(
        text=load_fixture("avaliable_channels_2g_data.json"),
        method="GET",
        url=get_url("xqnetwork/avaliable_channels", {"wifiIndex": 1}),
    )
    httpx_mock.add_response(
        text=load_fixture("avaliable_channels_5g_data.json"),
        method="GET",
        url=get_url("xqnetwork/avaliable_channels", {"wifiIndex": 2}),
    )
    httpx_mock.add_response(
        text=load_fixture("wan_info_data.json"),
        method="GET",
        url=get_url("xqnetwork/wan_info"),
    )
    httpx_mock.add_response(
        text=load_fixture("led_data.json"),
        method="GET",
        url=get_url("misystem/led", {}),
    )
    httpx_mock.add_response(
        text=load_fixture("device_list_data.json"),
        method="GET",
        url=get_url("misystem/devicelist"),
    )
    httpx_mock.add_response(
        text=load_fixture("wifi_connect_devices_data.json"),
        method="GET",
        url=get_url("xqnetwork/wifi_connect_devices"),
    )
    httpx_mock.add_response(
        text=load_fixture("rom_update_data.json"),
        method="GET",
        url=get_url("xqsystem/check_rom_update"),
    )

    with patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        diagnostics_data: dict = await async_get_config_entry_diagnostics(
            hass, config_entry
        )

        assert diagnostics_data["config_entry"] == async_redact_data(
            config_entry.as_dict(), TO_REDACT
        )
        assert diagnostics_data["data"] == async_redact_data(updater.data, TO_REDACT)
        assert diagnostics_data["devices"] == async_redact_data(
            updater.devices, TO_REDACT
        )
        assert diagnostics_data["requests"] == async_redact_data(
            updater.luci.diagnostics, TO_REDACT
        )
