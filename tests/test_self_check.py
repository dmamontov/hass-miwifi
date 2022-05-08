"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines,line-too-long

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, PropertyMock, patch
import pytest

from homeassistant.core import HomeAssistant

from custom_components.miwifi.exceptions import LuciException
from custom_components.miwifi.self_check import async_self_check
from custom_components.miwifi.updater import LuciUpdater

from tests.setup import (
    async_setup,
    async_mock_luci_client,
    MOCK_IP_ADDRESS,
)

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_supported(hass: HomeAssistant) -> None:
    """supported init.

    :param hass: HomeAssistant
    """

    def pn_check(hass: HomeAssistant, message: str, title: str) -> None:
        assert title == "MiWifi"
        assert (
            message
            == 'Router 192.168.31.1 not supported.\n\nModel: R3600\n\nCheck list:\n * xqsystem/login: 🟢\n * xqsystem/init_info: 🟢\n * misystem/status: 🟢\n * xqnetwork/mode: 🟢\n * misystem/topo_graph: 🟢\n * xqsystem/check_rom_update: 🟢\n * xqnetwork/wan_info: 🟢\n * misystem/led: 🟢\n * xqnetwork/wifi_detail_all: 🟢\n * xqnetwork/wifi_diag_detail_all: 🟢\n * xqnetwork/avaliable_channels: 🟢\n * xqnetwork/wifi_connect_devices: 🟢\n * misystem/devicelist: 🟢\n * xqnetwork/wifiap_signal: 🟢\n * misystem/newstatus: 🟢\n * xqsystem/reboot: ⚪\n * xqsystem/upgrade_rom: ⚪\n * xqsystem/flash_permission: ⚪\n * xqnetwork/set_wifi: ⚪\n * xqnetwork/set_wifi_without_restart: ⚪\n\n<a href="https://github.com/dmamontov/hass-miwifi/issues/new?title=Add+supports+R3600&body=Check+list%3A%0A+%2A+xqsystem%2Flogin%3A+%F0%9F%9F%A2%0A+%2A+xqsystem%2Finit_info%3A+%F0%9F%9F%A2%0A+%2A+misystem%2Fstatus%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Fmode%3A+%F0%9F%9F%A2%0A+%2A+misystem%2Ftopo_graph%3A+%F0%9F%9F%A2%0A+%2A+xqsystem%2Fcheck_rom_update%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Fwan_info%3A+%F0%9F%9F%A2%0A+%2A+misystem%2Fled%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Fwifi_detail_all%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Fwifi_diag_detail_all%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Favaliable_channels%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Fwifi_connect_devices%3A+%F0%9F%9F%A2%0A+%2A+misystem%2Fdevicelist%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Fwifiap_signal%3A+%F0%9F%9F%A2%0A+%2A+misystem%2Fnewstatus%3A+%F0%9F%9F%A2%0A+%2A+xqsystem%2Freboot%3A+%E2%9A%AA%0A+%2A+xqsystem%2Fupgrade_rom%3A+%E2%9A%AA%0A+%2A+xqsystem%2Fflash_permission%3A+%E2%9A%AA%0A+%2A+xqnetwork%2Fset_wifi%3A+%E2%9A%AA%0A+%2A+xqnetwork%2Fset_wifi_without_restart%3A+%E2%9A%AA" target="_blank">Create an issue with the data from this post to add support</a>'
        )

    with patch(
        "custom_components.miwifi.updater.LuciClient", new_callable=PropertyMock
    ) as mock_luci_client, patch(
        "custom_components.miwifi.self_check.pn.async_create", side_effect=pn_check
    ), patch(
        "custom_components.miwifi.updater.asyncio.sleep"
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.ip = MOCK_IP_ADDRESS

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await async_self_check(hass, updater.luci, "R3600")


async def test_unsupported(hass: HomeAssistant) -> None:
    """unsupported init.

    :param hass: HomeAssistant
    """

    def pn_check(hass: HomeAssistant, message: str, title: str) -> None:
        assert title == "MiWifi"
        assert (
            message
            == 'Router 192.168.31.1 not supported.\n\nModel: R3600\n\nCheck list:\n * xqsystem/login: 🟢\n * xqsystem/init_info: 🟢\n * misystem/status: 🟢\n * xqnetwork/mode: 🔴\n * misystem/topo_graph: 🟢\n * xqsystem/check_rom_update: 🟢\n * xqnetwork/wan_info: 🟢\n * misystem/led: 🟢\n * xqnetwork/wifi_detail_all: 🟢\n * xqnetwork/wifi_diag_detail_all: 🟢\n * xqnetwork/avaliable_channels: 🟢\n * xqnetwork/wifi_connect_devices: 🟢\n * misystem/devicelist: 🟢\n * xqnetwork/wifiap_signal: 🟢\n * misystem/newstatus: 🟢\n * xqsystem/reboot: ⚪\n * xqsystem/upgrade_rom: ⚪\n * xqsystem/flash_permission: ⚪\n * xqnetwork/set_wifi: ⚪\n * xqnetwork/set_wifi_without_restart: ⚪\n\n<a href="https://github.com/dmamontov/hass-miwifi/issues/new?title=Add+supports+R3600&body=Check+list%3A%0A+%2A+xqsystem%2Flogin%3A+%F0%9F%9F%A2%0A+%2A+xqsystem%2Finit_info%3A+%F0%9F%9F%A2%0A+%2A+misystem%2Fstatus%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Fmode%3A+%F0%9F%94%B4%0A+%2A+misystem%2Ftopo_graph%3A+%F0%9F%9F%A2%0A+%2A+xqsystem%2Fcheck_rom_update%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Fwan_info%3A+%F0%9F%9F%A2%0A+%2A+misystem%2Fled%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Fwifi_detail_all%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Fwifi_diag_detail_all%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Favaliable_channels%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Fwifi_connect_devices%3A+%F0%9F%9F%A2%0A+%2A+misystem%2Fdevicelist%3A+%F0%9F%9F%A2%0A+%2A+xqnetwork%2Fwifiap_signal%3A+%F0%9F%9F%A2%0A+%2A+misystem%2Fnewstatus%3A+%F0%9F%9F%A2%0A+%2A+xqsystem%2Freboot%3A+%E2%9A%AA%0A+%2A+xqsystem%2Fupgrade_rom%3A+%E2%9A%AA%0A+%2A+xqsystem%2Fflash_permission%3A+%E2%9A%AA%0A+%2A+xqnetwork%2Fset_wifi%3A+%E2%9A%AA%0A+%2A+xqnetwork%2Fset_wifi_without_restart%3A+%E2%9A%AA" target="_blank">Create an issue with the data from this post to add support</a>'
        )

    with patch(
        "custom_components.miwifi.updater.LuciClient", new_callable=PropertyMock
    ) as mock_luci_client, patch(
        "custom_components.miwifi.self_check.pn.async_create", side_effect=pn_check
    ), patch(
        "custom_components.miwifi.updater.asyncio.sleep"
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.mode = AsyncMock(side_effect=LuciException)
        mock_luci_client.return_value.ip = MOCK_IP_ADDRESS

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await async_self_check(hass, updater.luci, "R3600")
