"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import json
import logging
from typing import Final
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.storage import Store
from httpx import codes
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from custom_components.miwifi.const import (
    ATTR_BINARY_SENSOR_DUAL_BAND,
    ATTR_BINARY_SENSOR_WAN_STATE,
    ATTR_LIGHT_LED,
    ATTR_SELECT_WIFI_2_4_CHANNEL,
    ATTR_SELECT_WIFI_2_4_CHANNELS,
    ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH,
    ATTR_SELECT_WIFI_5_0_CHANNEL,
    ATTR_SELECT_WIFI_5_0_CHANNELS,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNEL,
    ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH,
    ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH,
    ATTR_SENSOR_MODE,
    ATTR_STATE,
    ATTR_SWITCH_WIFI_2_4,
    ATTR_SWITCH_WIFI_5_0,
    ATTR_SWITCH_WIFI_5_0_GAME,
    ATTR_SWITCH_WIFI_GUEST,
    ATTR_UPDATE_CURRENT_VERSION,
    ATTR_UPDATE_DOWNLOAD_URL,
    ATTR_UPDATE_FILE_HASH,
    ATTR_UPDATE_FILE_SIZE,
    ATTR_UPDATE_FIRMWARE,
    ATTR_UPDATE_LATEST_VERSION,
    ATTR_UPDATE_RELEASE_URL,
    ATTR_UPDATE_TITLE,
    ATTR_WIFI_2_4_DATA,
    ATTR_WIFI_5_0_DATA,
    ATTR_WIFI_5_0_GAME_DATA,
    ATTR_WIFI_GUEST_DATA,
    DEFAULT_MANUFACTURER,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.miwifi.enum import Mode
from custom_components.miwifi.exceptions import LuciError, LuciRequestError
from custom_components.miwifi.luci import LuciClient
from custom_components.miwifi.updater import LuciUpdater, async_get_updater
from tests.setup import MultipleSideEffect, async_mock_luci_client, async_setup

MOCK_IP_ADDRESS: Final = "192.168.31.1"
MOCK_PASSWORD: Final = "**REDACTED**"

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


@pytest.mark.asyncio
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
    assert updater._activity_days == 0
    assert not updater._is_only_login
    assert isinstance(updater.data, dict)
    assert len(updater.data) == 0
    assert isinstance(updater.devices, dict)
    assert len(updater.devices) == 0
    assert updater.code == codes.BAD_GATEWAY
    assert updater.new_device_callback is not None
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
        (CONF_IP_ADDRESS, "192.168.31.1"),
        (CONNECTION_NETWORK_MAC, MOCK_IP_ADDRESS),
    }
    assert updater.device_info["name"] == DEFAULT_NAME
    assert updater.device_info["manufacturer"] == DEFAULT_MANUFACTURER
    assert updater.device_info["model"] is None
    assert updater.device_info["sw_version"] is None
    assert updater.device_info["configuration_url"] == f"http://{MOCK_IP_ADDRESS}/"


@pytest.mark.asyncio
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
        mock_luci_client.return_value.login = AsyncMock(side_effect=LuciRequestError)
        mock_asyncio_sleep.return_value = Mock(return_value=None)

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        with pytest.raises(LuciError):
            await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert updater.code == codes.FORBIDDEN


@pytest.mark.asyncio
async def test_updater_reauthorization(hass: HomeAssistant) -> None:
    """Test updater reauthorization.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        def login_success() -> dict:
            return json.loads(load_fixture("status_data.json"))

        def login_error() -> None:
            raise LuciRequestError

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


@pytest.mark.asyncio
async def test_updater_skip_method(hass: HomeAssistant) -> None:
    """Test updater skip unsupported method.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.LuciClient.new_status"
    ) as mock_new_status, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
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


@pytest.mark.asyncio
async def test_updater_without_model_info(hass: HomeAssistant) -> None:
    """Test updater without model info.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
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


@pytest.mark.asyncio
async def test_updater_undefined_router(hass: HomeAssistant) -> None:
    """Test updater undefined router config.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_self_check", return_value=None
    ) as mock_async_self_check, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.init_info = AsyncMock(
            return_value=json.loads(
                load_fixture("init_info_undefined_router_data.json")
            )
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        with pytest.raises(LuciError):
            await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert len(mock_async_self_check.mock_calls) == 1


@pytest.mark.asyncio
async def test_updater_without_hardware_info(hass: HomeAssistant) -> None:
    """Test updater without hardware info.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.pn.async_create", return_value=None
    ) as mock_async_create_pm, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.init_info = AsyncMock(
            return_value=json.loads(
                load_fixture("init_info_without_hardware_data.json")
            )
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        with pytest.raises(LuciError):
            await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert len(mock_async_create_pm.mock_calls) == 1


@pytest.mark.asyncio
async def test_updater_without_version_info(hass: HomeAssistant) -> None:
    """Test updater without version info.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.status = AsyncMock(
            return_value=json.loads(load_fixture("status_without_version_data.json"))
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()
        await hass.async_block_till_done()

    assert ATTR_UPDATE_CURRENT_VERSION not in updater.data


@pytest.mark.asyncio
async def test_updater_raise_rom_update(hass: HomeAssistant) -> None:
    """Test updater raise rom update.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.rom_update = AsyncMock(side_effect=LuciError)

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()
        await hass.async_block_till_done()

    assert updater.data[ATTR_UPDATE_FIRMWARE] == {
        ATTR_UPDATE_CURRENT_VERSION: "3.0.34",
        ATTR_UPDATE_LATEST_VERSION: "3.0.34",
        ATTR_UPDATE_TITLE: "Xiaomi RA67 (XIAOMI RA67)",
    }


@pytest.mark.asyncio
async def test_updater_need_rom_update(hass: HomeAssistant) -> None:
    """Test updater need rom update.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.rom_update = AsyncMock(
            return_value=json.loads(load_fixture("rom_update_need_data.json"))
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()
        await hass.async_block_till_done()

    assert updater.data[ATTR_UPDATE_FIRMWARE] == {
        ATTR_UPDATE_CURRENT_VERSION: "3.0.34",
        ATTR_UPDATE_LATEST_VERSION: "3.0.35",
        ATTR_UPDATE_TITLE: "Xiaomi RA67 (XIAOMI RA67)",
        ATTR_UPDATE_DOWNLOAD_URL: "https://miwifi.com/download",
        ATTR_UPDATE_RELEASE_URL: "https://miwifi.com/changelog",
        ATTR_UPDATE_FILE_SIZE: 10,
        ATTR_UPDATE_FILE_HASH: "12345",
    }


@pytest.mark.asyncio
async def test_updater_key_error_rom_update(hass: HomeAssistant) -> None:
    """Test updater key error rom update.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.rom_update = AsyncMock(
            return_value=json.loads(load_fixture("rom_update_key_error_data.json"))
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert ATTR_UPDATE_FIRMWARE not in updater.data


@pytest.mark.asyncio
async def test_updater_skip_mode_mesh(hass: HomeAssistant) -> None:
    """Test updater key error rom update.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]
        updater.data[ATTR_SENSOR_MODE] = Mode.MESH

        await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert updater.data[ATTR_SENSOR_MODE] == Mode.MESH


@pytest.mark.asyncio
async def test_updater_value_error_mode(hass: HomeAssistant) -> None:
    """Test updater value error mode.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.mode = AsyncMock(
            return_value=json.loads(load_fixture("mode_value_error_data.json"))
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert updater.data[ATTR_SENSOR_MODE] == Mode.DEFAULT


@pytest.mark.asyncio
async def test_updater_incorrect_wan_info(hass: HomeAssistant) -> None:
    """Test updater incorrect wan info.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.wan_info = AsyncMock(
            return_value=json.loads(load_fixture("wan_info_incorrect_data.json"))
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert not updater.data[ATTR_BINARY_SENSOR_WAN_STATE]


@pytest.mark.asyncio
async def test_updater_incorrect_led(hass: HomeAssistant) -> None:
    """Test updater incorrect led.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.led = AsyncMock(
            return_value=json.loads(load_fixture("led_incorrect_data.json"))
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert not updater.data[ATTR_LIGHT_LED]


@pytest.mark.asyncio
async def test_updater_undefined_bsd_wifi_info(hass: HomeAssistant) -> None:
    """Test updater undefined bsd wifi info.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            return_value=json.loads(
                load_fixture("wifi_detail_all_undefined_bsd_data.json")
            )
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert not updater.data[ATTR_BINARY_SENSOR_DUAL_BAND]


@pytest.mark.asyncio
async def test_updater_empty_wifi_info(hass: HomeAssistant) -> None:
    """Test updater empty wifi info.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            return_value=json.loads(load_fixture("wifi_detail_all_empty_data.json"))
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert ATTR_SWITCH_WIFI_2_4 not in updater.data
    assert ATTR_WIFI_2_4_DATA not in updater.data
    assert ATTR_SWITCH_WIFI_5_0 not in updater.data
    assert ATTR_WIFI_5_0_DATA not in updater.data
    assert ATTR_SWITCH_WIFI_5_0_GAME not in updater.data
    assert ATTR_WIFI_5_0_GAME_DATA not in updater.data
    assert ATTR_SWITCH_WIFI_GUEST not in updater.data
    assert ATTR_WIFI_GUEST_DATA not in updater.data

    assert ATTR_SELECT_WIFI_2_4_CHANNEL not in updater.data
    assert ATTR_SELECT_WIFI_5_0_CHANNEL not in updater.data
    assert ATTR_SELECT_WIFI_5_0_GAME_CHANNEL not in updater.data

    assert ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH not in updater.data
    assert ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH not in updater.data
    assert ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH not in updater.data


@pytest.mark.asyncio
async def test_updater_unsupported_guest_wifi_info(hass: HomeAssistant) -> None:
    """Test updater unsupported guest wifi info.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.wifi_diag_detail_all = AsyncMock(
            return_value=json.loads(
                load_fixture("wifi_diag_detail_all_unsupported_guest_data.json")
            )
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert ATTR_SWITCH_WIFI_GUEST not in updater.data
    assert ATTR_WIFI_GUEST_DATA not in updater.data
    assert not updater.supports_guest


@pytest.mark.asyncio
async def test_updater_error_guest_wifi_info(hass: HomeAssistant) -> None:
    """Test updater error guest wifi info.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.wifi_diag_detail_all = AsyncMock(
            side_effect=LuciError
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert ATTR_SWITCH_WIFI_GUEST not in updater.data
    assert ATTR_WIFI_GUEST_DATA not in updater.data
    assert not updater.supports_guest


@pytest.mark.asyncio
async def test_updater_is_absent_ifname_wifi_info(hass: HomeAssistant) -> None:
    """Test updater is absent ifname wifi info.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            return_value=json.loads(
                load_fixture("wifi_detail_all_is_absent_ifname_data.json")
            )
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert ATTR_SWITCH_WIFI_2_4 not in updater.data
    assert ATTR_WIFI_2_4_DATA not in updater.data

    assert ATTR_SELECT_WIFI_2_4_CHANNEL not in updater.data

    assert ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH not in updater.data


@pytest.mark.asyncio
async def test_updater_undefined_ifname_wifi_info(hass: HomeAssistant) -> None:
    """Test updater undefined ifname wifi info.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            return_value=json.loads(
                load_fixture("wifi_detail_all_undefined_ifname_data.json")
            )
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert ATTR_SWITCH_WIFI_2_4 not in updater.data
    assert ATTR_WIFI_2_4_DATA not in updater.data

    assert ATTR_SELECT_WIFI_2_4_CHANNEL not in updater.data

    assert ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH not in updater.data


@pytest.mark.asyncio
async def test_updater_empty_2g_avaliable_channels(hass: HomeAssistant) -> None:
    """Test updater empty 2g avaliable channels.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        async def mock_avaliable_channels(index: int = 1) -> dict:
            """Mock channels"""

            if index == 2:
                return json.loads(load_fixture("avaliable_channels_5g_data.json"))

            return json.loads(load_fixture("avaliable_channels_empty_2g_data.json"))

        mock_luci_client.return_value.avaliable_channels = AsyncMock(
            side_effect=mock_avaliable_channels
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()

        await hass.async_block_till_done()

    assert ATTR_SELECT_WIFI_2_4_CHANNELS not in updater.data
    assert ATTR_SELECT_WIFI_5_0_CHANNELS in updater.data


@pytest.mark.asyncio
async def test_updater_without_store(hass: HomeAssistant) -> None:
    """Test updater without_store.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.helper.Store"
    ) as mock_store, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_store.return_value.async_load = AsyncMock(return_value=None)
        mock_store.return_value.async_save = AsyncMock(return_value=None)

        setup_data: list = await async_setup(hass, without_store=True)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()
        await updater.async_stop()

        await hass.async_block_till_done()

    assert len(mock_store.mock_calls) == 0


@pytest.mark.asyncio
async def test_updater_with_clean_store(hass: HomeAssistant) -> None:
    """Test updater with clean store.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]

        await updater.async_config_entry_first_refresh()
        await updater.async_stop(clean_store=True)

        await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_get_updater_by_ip_error(hass: HomeAssistant) -> None:
    """Test updater by ip error.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
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
            async_get_updater(hass, "test")

        assert str(error.value) == "Integration with identifier: test not found."
