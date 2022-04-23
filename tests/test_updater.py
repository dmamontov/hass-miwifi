"""Tests for the miwifi component."""

from __future__ import annotations

from typing import Final
import logging
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from pytest_homeassistant_custom_component.common import load_fixture

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.storage import Store
from httpx import codes

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.miwifi.const import (
    DOMAIN,
    ATTR_STATE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_ACTIVITY_DAYS,
    DEFAULT_NAME,
    DEFAULT_MANUFACTURER,
    ATTR_UPDATE_CURRENT_VERSION,
)
from custom_components.miwifi.exceptions import (
    LuciException,
    LuciTokenException,
)
from custom_components.miwifi.luci import LuciClient
from custom_components.miwifi.updater import LuciUpdater

from tests.setup import async_setup, async_mock_luci_client, MultipleSideEffect

MOCK_IP_ADDRESS: Final = "192.168.31.1"
MOCK_PASSWORD: Final = "**REDACTED**"

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_updater(hass: HomeAssistant) -> None:
    """Test updater.

    :param hass: HomeAssistant
    """

    setup_data: list = await async_setup(hass)

    updater: LuciUpdater = setup_data[0]
    config_entry: MockConfigEntry = setup_data[1]

    assert updater._unsub_refresh is None

    updater.schedule_refresh(updater._update_interval)
    updater.schedule_refresh(updater._update_interval)

    assert updater._unsub_refresh is not None

    assert isinstance(updater.luci, LuciClient)
    assert updater.ip == MOCK_IP_ADDRESS
    assert not updater.is_force_load
    assert isinstance(updater._store, Store)
    assert updater._entry_id == config_entry.entry_id
    assert updater._scan_interval == DEFAULT_SCAN_INTERVAL
    assert updater._activity_days == DEFAULT_ACTIVITY_DAYS
    assert not updater._is_only_login
    assert isinstance(updater.data, dict)
    assert len(updater.data) == 0
    assert isinstance(updater.devices, dict)
    assert len(updater.devices) == 0
    assert updater.code == codes.BAD_GATEWAY
    assert updater.new_device_callback is not None
    assert isinstance(updater._manufacturers, dict)
    assert len(updater._manufacturers) == 0
    assert updater._is_reauthorization
    assert updater._is_first_update
    assert isinstance(updater._signals, dict)
    assert len(updater._signals) == 0
    assert isinstance(updater._moved_devices, list)
    assert len(updater._moved_devices) == 0
    assert str(updater._update_interval) == "0:00:30"
    assert not updater.is_repeater
    assert updater.device_info["identifiers"] == {(DOMAIN, MOCK_IP_ADDRESS)}
    assert updater.device_info["connections"] == {
        (CONNECTION_NETWORK_MAC, MOCK_IP_ADDRESS)
    }
    assert updater.device_info["name"] == DEFAULT_NAME
    assert updater.device_info["manufacturer"] == DEFAULT_MANUFACTURER
    assert updater.device_info["model"] is None
    assert updater.device_info["sw_version"] is None
    assert updater.device_info["configuration_url"] == f"http://{MOCK_IP_ADDRESS}/"


async def test_updater_login_fail(hass: HomeAssistant) -> None:
    """Test updater login_fail.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep"
    ) as mock_asyncio_sleep:
        await async_mock_luci_client(mock_luci_client)
        mock_luci_client.return_value.login = AsyncMock(side_effect=LuciTokenException)
        mock_asyncio_sleep.return_value = Mock(return_value=None)

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        with pytest.raises(LuciException):
            await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert updater.code == codes.FORBIDDEN
    assert len(mock_asyncio_sleep.mock_calls) == 14
    assert len(mock_luci_client.mock_calls) == 13


async def test_updater_reauthorization(hass: HomeAssistant) -> None:
    """Test updater reauthorization.

    :param hass: HomeAssistant
    """

    with patch("custom_components.miwifi.updater.LuciClient") as mock_luci_client:
        await async_mock_luci_client(mock_luci_client)

        def login_success() -> dict:
            return json.loads(load_fixture("status_data.json"))

        def login_error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.status = AsyncMock(
            side_effect=MultipleSideEffect(login_success, login_error, login_error)
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()
        await hass.async_block_till_done()

        assert updater.code == codes.OK
        assert not updater._is_reauthorization
        assert updater.data[ATTR_STATE]

        await updater.update()
        await hass.async_block_till_done()

        assert updater.code == codes.FORBIDDEN
        assert updater._is_reauthorization
        assert updater.data[ATTR_STATE]

        await updater.update()
        await hass.async_block_till_done()

        assert updater.code == codes.FORBIDDEN
        assert updater._is_reauthorization
        assert not updater.data[ATTR_STATE]


async def test_updater_skip_method(hass: HomeAssistant) -> None:
    """Test updater skip unsupported method.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.LuciClient.new_status"
    ) as mock_new_status:
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.init_info = AsyncMock(
            return_value=json.loads(
                load_fixture("init_info_unsupported_methods_data.json")
            )
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()
        await hass.async_block_till_done()

    assert updater.code == codes.OK
    assert len(mock_new_status.mock_calls) == 0


async def test_updater_without_model_info(hass: HomeAssistant) -> None:
    """Test updater without model info.

    :param hass: HomeAssistant
    """

    with patch("custom_components.miwifi.updater.LuciClient") as mock_luci_client:
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.init_info = AsyncMock(
            return_value=json.loads(load_fixture("init_info_without_model_data.json"))
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()
        await hass.async_block_till_done()

    assert updater.code == codes.OK
    assert updater.device_info["model"] == "RA67"
    assert updater.device_info["manufacturer"] == DEFAULT_MANUFACTURER


async def test_updater_undefined_router(hass: HomeAssistant) -> None:
    """Test updater undefined router config.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_self_check", return_value=None
    ) as mock_async_self_check:
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.init_info = AsyncMock(
            return_value=json.loads(
                load_fixture("init_info_undefined_router_data.json")
            )
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        with pytest.raises(LuciException):
            await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert len(mock_async_self_check.mock_calls) == 1


async def test_updater_without_hardware_info(hass: HomeAssistant) -> None:
    """Test updater without hardware info.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.pn.async_create", return_value=None
    ) as mock_async_create_pm:
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.init_info = AsyncMock(
            return_value=json.loads(
                load_fixture("init_info_without_hardware_data.json")
            )
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        with pytest.raises(LuciException):
            await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert len(mock_async_create_pm.mock_calls) == 1


async def test_updater_without_version_info(hass: HomeAssistant) -> None:
    """Test updater without version info.

    :param hass: HomeAssistant
    """

    with patch("custom_components.miwifi.updater.LuciClient") as mock_luci_client:
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.status = AsyncMock(
            return_value=json.loads(load_fixture("status_without_version_data.json"))
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()
        await hass.async_block_till_done()

    assert ATTR_UPDATE_CURRENT_VERSION not in updater.data
