"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch
import json
import pytest

from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from custom_components.miwifi.const import (
    DOMAIN,
    NAME,
    SERVICE_CALC_PASSWD,
)
from custom_components.miwifi.exceptions import NotSupportedError

from tests.setup import async_mock_luci_client, async_setup, MOCK_IP_ADDRESS

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_calc_passwd(hass: HomeAssistant) -> None:
    """Test calc passwd.

    :param hass: HomeAssistant
    """

    def pn_check(hass: HomeAssistant, message: str, title: str) -> None:
        assert title == NAME
        assert message == "Your passwd: 0f2d9073"

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
        "custom_components.miwifi.services.pn.async_create", side_effect=pn_check
    ):
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        assert await hass.services.async_call(
            DOMAIN,
            SERVICE_CALC_PASSWD,
            {CONF_IP_ADDRESS: MOCK_IP_ADDRESS},
            blocking=True,
            limit=None,
        )


async def test_calc_passwd_incorrect_ip(hass: HomeAssistant) -> None:
    """Test calc passwd incorrect ip.

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
    ):
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        with pytest.raises(ValueError) as error:
            await hass.services.async_call(
                DOMAIN,
                SERVICE_CALC_PASSWD,
                {CONF_IP_ADDRESS: "127.0.0.1"},
                blocking=True,
                limit=None,
            )

        assert str(error.value) == "Integration with ip address: 127.0.0.1 not found."


async def test_calc_passwd_unsupported(hass: HomeAssistant) -> None:
    """Test calc passwd unsupported.

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
    ):
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.status = AsyncMock(
            return_value=json.loads(load_fixture("status_without_version_data.json"))
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        with pytest.raises(NotSupportedError) as error:
            await hass.services.async_call(
                DOMAIN,
                SERVICE_CALC_PASSWD,
                {CONF_IP_ADDRESS: MOCK_IP_ADDRESS},
                blocking=True,
                limit=None,
            )

        assert (
            str(error.value)
            == f"Integration with ip address: {MOCK_IP_ADDRESS} does not support this service."
        )
