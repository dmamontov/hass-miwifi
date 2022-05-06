"""Tests for the miwifi component."""

from __future__ import annotations

from datetime import timedelta
import logging
from unittest.mock import AsyncMock, patch
import pytest
import json
from homeassistant.components.select import (
    ENTITY_ID_FORMAT as SELECT_ENTITY_ID_FORMAT,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_OPTION,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util.dt import utcnow

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    load_fixture,
    async_fire_time_changed,
)

from custom_components.miwifi.const import (
    DOMAIN,
    UPDATER,
    DEFAULT_SCAN_INTERVAL,
    ATTRIBUTION,
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_WIFI_2_4_DATA,
    ATTR_WIFI_5_0_DATA,
    ATTR_WIFI_5_0_GAME_DATA,
    ATTR_SELECT_WIFI_2_4_CHANNEL_NAME,
    ATTR_SELECT_WIFI_2_4_CHANNEL_OPTIONS,
    ATTR_SELECT_WIFI_5_0_CHANNEL_NAME,
    ATTR_SELECT_WIFI_5_0_CHANNEL_OPTIONS,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_NAME,
    ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_OPTIONS,
    ATTR_SELECT_SIGNAL_STRENGTH_OPTIONS,
    ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH_NAME,
    ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH_NAME,
    ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH_NAME,
)
from custom_components.miwifi.exceptions import LuciTokenException
from custom_components.miwifi.helper import generate_entity_id
from custom_components.miwifi.updater import LuciUpdater

from tests.setup import async_mock_luci_client, async_setup, MultipleSideEffect

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
    ):
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_2_4_CHANNEL_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_5_0_CHANNEL_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH_NAME, updater
        )
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH_NAME, updater
        )
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH_NAME, updater
        )
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None


async def test_init_with_game(hass: HomeAssistant) -> None:
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
    ):
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            return_value=json.loads(load_fixture("wifi_detail_all_with_game_data.json"))
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_2_4_CHANNEL_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_5_0_CHANNEL_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH_NAME, updater
        )
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH_NAME, updater
        )
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH_NAME, updater
        )
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None


async def test_update_channel_2_4(hass: HomeAssistant) -> None:
    """Test update channel 2.4.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(success, success, success, error, error)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_2_4_CHANNEL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)

        assert entry.disabled_by is None
        assert state.state == "2"
        assert state.name == ATTR_SELECT_WIFI_2_4_CHANNEL_NAME
        assert state.attributes["icon"] == "mdi:format-list-numbered"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["options"] == ATTR_SELECT_WIFI_2_4_CHANNEL_OPTIONS
        assert entry.entity_category == EntityCategory.CONFIG

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "2"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_channel_2_4_empty_channels(hass: HomeAssistant) -> None:
    """Test update channel 2.4.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        mock_luci_client.return_value.avaliable_channels = AsyncMock(
            return_value={"list": []}
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_2_4_CHANNEL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)

        assert entry.disabled_by is None
        assert state.attributes["options"] == ATTR_SELECT_WIFI_2_4_CHANNEL_OPTIONS


async def test_update_channel_2_4_wifi_data(hass: HomeAssistant) -> None:
    """Test update channel 2.4.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_data.json"))

        def change_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_change_data.json"))

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            side_effect=MultipleSideEffect(
                success_wifi_data,
                success_wifi_data,
                success_wifi_data,
                change_wifi_data,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_2_4_DATA) == {
            "ssid": "**REDACTED**",
            "pwd": "**REDACTED**",
            "encryption": "psk2",
            "channel": 2,
            "bandwidth": "20",
            "txpwr": "max",
            "hidden": "0",
            "on": "1",
            "txbf": "3",
        }

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_2_4_CHANNEL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)

        assert entry.disabled_by is None

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_2_4_DATA) == {
            "ssid": "**REDACTED**",
            "pwd": "**REDACTED**",
            "encryption": "psk2",
            "channel": 2,
            "bandwidth": "20",
            "txpwr": "min",
            "hidden": "0",
            "on": "1",
            "txbf": "3",
        }


async def test_update_channel_2_4_change_channel(hass: HomeAssistant) -> None:
    """Test update channel 2.4.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success_set_wifi(data: dict) -> dict:
            return {"code": 0}

        def error_set_wifi(data: dict) -> None:
            raise LuciTokenException

        mock_luci_client.return_value.set_wifi = AsyncMock(
            side_effect=MultipleSideEffect(
                success_set_wifi,
                error_set_wifi,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_2_4_CHANNEL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)

        assert entry.disabled_by is None

        _prev_calls: int = len(mock_luci_client.mock_calls)

        assert await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: [unique_id], ATTR_OPTION: "10"},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == "10"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 1

        assert await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: [unique_id], ATTR_OPTION: "10"},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == "10"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 2


async def test_update_channel_5_0(hass: HomeAssistant) -> None:
    """Test update channel 5.0.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(success, success, success, error, error)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_5_0_CHANNEL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)

        assert entry.disabled_by is None
        assert state.state == "149"
        assert state.name == ATTR_SELECT_WIFI_5_0_CHANNEL_NAME
        assert state.attributes["icon"] == "mdi:format-list-numbered"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["options"] == [
            "36",
            "40",
            "44",
            "48",
            "149",
            "153",
            "157",
            "161",
        ]
        assert entry.entity_category == EntityCategory.CONFIG

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "149"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_channel_5_0_empty_channels(hass: HomeAssistant) -> None:
    """Test update channel 5.0.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        mock_luci_client.return_value.avaliable_channels = AsyncMock(
            return_value={"list": []}
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_5_0_CHANNEL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)

        assert entry.disabled_by is None
        assert state.attributes["options"] == ATTR_SELECT_WIFI_5_0_CHANNEL_OPTIONS


async def test_update_channel_5_0_empty_channels_and_5g_game(
    hass: HomeAssistant,
) -> None:
    """Test update channel 5.0.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        mock_luci_client.return_value.avaliable_channels = AsyncMock(
            return_value={"list": []}
        )

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            return_value=json.loads(load_fixture("wifi_detail_all_with_game_data.json"))
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_5_0_CHANNEL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)

        assert entry.disabled_by is None
        assert state.attributes["options"] == ["149", "153", "157", "161", "165"]


async def test_update_channel_5_0_wifi_data(hass: HomeAssistant) -> None:
    """Test update channel 5.0.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_data.json"))

        def change_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_change_data.json"))

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            side_effect=MultipleSideEffect(
                success_wifi_data,
                success_wifi_data,
                success_wifi_data,
                change_wifi_data,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_5_0_DATA) == {
            "ssid": "**REDACTED**",
            "pwd": "**REDACTED**",
            "encryption": "psk2",
            "channel": 149,
            "bandwidth": "0",
            "txpwr": "max",
            "hidden": "0",
            "on": "1",
            "txbf": "3",
        }

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_5_0_CHANNEL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)

        assert entry.disabled_by is None

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_5_0_DATA) == {
            "ssid": "**REDACTED**",
            "pwd": "**REDACTED**",
            "encryption": "psk2",
            "channel": 149,
            "bandwidth": "0",
            "txpwr": "min",
            "hidden": "0",
            "on": "1",
            "txbf": "3",
        }


async def test_update_channel_5_0_change_channel(hass: HomeAssistant) -> None:
    """Test update channel 5.0.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success_set_wifi(data: dict) -> dict:
            return {"code": 0}

        def error_set_wifi(data: dict) -> None:
            raise LuciTokenException

        mock_luci_client.return_value.set_wifi = AsyncMock(
            side_effect=MultipleSideEffect(
                success_set_wifi,
                error_set_wifi,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_5_0_CHANNEL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)

        assert entry.disabled_by is None

        _prev_calls: int = len(mock_luci_client.mock_calls)

        assert await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: [unique_id], ATTR_OPTION: "48"},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == "48"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 1

        assert await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: [unique_id], ATTR_OPTION: "44"},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == "44"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 2


async def test_update_channel_5_0_game(hass: HomeAssistant) -> None:
    """Test update channel 5.0 game.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(success, success, success, error, error)
        )

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            return_value=json.loads(load_fixture("wifi_detail_all_with_game_data.json"))
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)

        assert entry.disabled_by is None
        assert state.state == "48"
        assert state.name == ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_NAME
        assert state.attributes["icon"] == "mdi:format-list-numbered"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["options"] == ["36", "40", "44", "48"]
        assert entry.entity_category == EntityCategory.CONFIG

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "48"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_channel_5_0_game_empty_channels(hass: HomeAssistant) -> None:
    """Test update channel 5.0 game.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        mock_luci_client.return_value.avaliable_channels = AsyncMock(
            return_value={"list": []}
        )

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            return_value=json.loads(load_fixture("wifi_detail_all_with_game_data.json"))
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)

        assert entry.disabled_by is None
        assert state.attributes["options"] == ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_OPTIONS


async def test_update_channel_5_0_game_wifi_data(hass: HomeAssistant) -> None:
    """Test update channel 5.0 game.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_with_game_data.json"))

        def change_wifi_data() -> dict:
            return json.loads(
                load_fixture("wifi_detail_all_with_game_change_data.json")
            )

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            side_effect=MultipleSideEffect(
                success_wifi_data,
                success_wifi_data,
                success_wifi_data,
                change_wifi_data,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_5_0_GAME_DATA) == {
            "ssid": "**REDACTED**",
            "pwd": "**REDACTED**",
            "encryption": "psk2",
            "channel": 48,
            "bandwidth": "0",
            "txpwr": "max",
            "hidden": "0",
            "on": "1",
            "txbf": "3",
        }

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)

        assert entry.disabled_by is None

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_5_0_GAME_DATA) == {
            "ssid": "**REDACTED**",
            "pwd": "**REDACTED**",
            "encryption": "psk2",
            "channel": 48,
            "bandwidth": "0",
            "txpwr": "min",
            "hidden": "0",
            "on": "1",
            "txbf": "3",
        }


async def test_update_channel_5_0_game_change_channel(hass: HomeAssistant) -> None:
    """Test update channel 5.0 game.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            return_value=json.loads(load_fixture("wifi_detail_all_with_game_data.json"))
        )

        def success_set_wifi(data: dict) -> dict:
            return {"code": 0}

        def error_set_wifi(data: dict) -> None:
            raise LuciTokenException

        mock_luci_client.return_value.set_wifi = AsyncMock(
            side_effect=MultipleSideEffect(
                success_set_wifi,
                error_set_wifi,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)

        assert entry.disabled_by is None

        _prev_calls: int = len(mock_luci_client.mock_calls)

        assert await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: [unique_id], ATTR_OPTION: "36"},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == "36"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 1

        assert await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: [unique_id], ATTR_OPTION: "40"},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == "40"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 2


async def test_update_strength_2_4(hass: HomeAssistant) -> None:
    """Test update strength 2.4.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(success, success, success, error, error)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH_NAME, updater
        )

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)

        assert entry.disabled_by is None
        assert state.state == "max"
        assert state.name == ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH_NAME
        assert state.attributes["icon"] == "mdi:wifi-strength-4"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["options"] == ATTR_SELECT_SIGNAL_STRENGTH_OPTIONS
        assert entry.entity_category == EntityCategory.CONFIG

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "max"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_strength_2_4_wifi_data(hass: HomeAssistant) -> None:
    """Test update strength 2.4.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_data.json"))

        def change_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_change_data.json"))

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            side_effect=MultipleSideEffect(
                success_wifi_data,
                success_wifi_data,
                success_wifi_data,
                change_wifi_data,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_2_4_DATA) == {
            "ssid": "**REDACTED**",
            "pwd": "**REDACTED**",
            "encryption": "psk2",
            "channel": 2,
            "bandwidth": "20",
            "txpwr": "max",
            "hidden": "0",
            "on": "1",
            "txbf": "3",
        }

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH_NAME, updater
        )

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)

        assert entry.disabled_by is None

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_2_4_DATA) == {
            "ssid": "**REDACTED**",
            "pwd": "**REDACTED**",
            "encryption": "psk2",
            "channel": 2,
            "bandwidth": "20",
            "txpwr": "min",
            "hidden": "0",
            "on": "1",
            "txbf": "3",
        }


async def test_update_strength_2_4_change_strength(hass: HomeAssistant) -> None:
    """Test update strength 2.4.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success_set_wifi(data: dict) -> dict:
            return {"code": 0}

        def error_set_wifi(data: dict) -> None:
            raise LuciTokenException

        mock_luci_client.return_value.set_wifi = AsyncMock(
            side_effect=MultipleSideEffect(
                success_set_wifi,
                error_set_wifi,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH_NAME, updater
        )

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)

        assert entry.disabled_by is None

        state: State = hass.states.get(unique_id)
        assert state.attributes["icon"] == "mdi:wifi-strength-4"

        _prev_calls: int = len(mock_luci_client.mock_calls)

        assert await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: [unique_id], ATTR_OPTION: "min"},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == "min"
        assert state.attributes["icon"] == "mdi:wifi-strength-1"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 1

        assert await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: [unique_id], ATTR_OPTION: "mid"},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == "mid"
        assert state.attributes["icon"] == "mdi:wifi-strength-2"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 2


async def test_update_strength_5_0(hass: HomeAssistant) -> None:
    """Test update strength 5.0.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(success, success, success, error, error)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH_NAME, updater
        )

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)

        assert entry.disabled_by is None
        assert state.state == "max"
        assert state.name == ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH_NAME
        assert state.attributes["icon"] == "mdi:wifi-strength-4"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["options"] == ATTR_SELECT_SIGNAL_STRENGTH_OPTIONS
        assert entry.entity_category == EntityCategory.CONFIG

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "max"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_strength_5_0_wifi_data(hass: HomeAssistant) -> None:
    """Test update strength 5.0.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_data.json"))

        def change_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_change_data.json"))

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            side_effect=MultipleSideEffect(
                success_wifi_data,
                success_wifi_data,
                success_wifi_data,
                change_wifi_data,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_5_0_DATA) == {
            "ssid": "**REDACTED**",
            "pwd": "**REDACTED**",
            "encryption": "psk2",
            "channel": 149,
            "bandwidth": "0",
            "txpwr": "max",
            "hidden": "0",
            "on": "1",
            "txbf": "3",
        }

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH_NAME, updater
        )

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)

        assert entry.disabled_by is None

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_5_0_DATA) == {
            "ssid": "**REDACTED**",
            "pwd": "**REDACTED**",
            "encryption": "psk2",
            "channel": 149,
            "bandwidth": "0",
            "txpwr": "min",
            "hidden": "0",
            "on": "1",
            "txbf": "3",
        }


async def test_update_strength_5_0_change_channel(hass: HomeAssistant) -> None:
    """Test update strength 5.0.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success_set_wifi(data: dict) -> dict:
            return {"code": 0}

        def error_set_wifi(data: dict) -> None:
            raise LuciTokenException

        mock_luci_client.return_value.set_wifi = AsyncMock(
            side_effect=MultipleSideEffect(
                success_set_wifi,
                error_set_wifi,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH_NAME, updater
        )

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)

        assert entry.disabled_by is None

        state = hass.states.get(unique_id)
        assert state.attributes["icon"] == "mdi:wifi-strength-4"

        _prev_calls: int = len(mock_luci_client.mock_calls)

        assert await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: [unique_id], ATTR_OPTION: "min"},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == "min"
        assert state.attributes["icon"] == "mdi:wifi-strength-1"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 1

        assert await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: [unique_id], ATTR_OPTION: "mid"},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == "mid"
        assert state.attributes["icon"] == "mdi:wifi-strength-2"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 2


async def test_update_strength_5_0_game(hass: HomeAssistant) -> None:
    """Test update strength 5.0 game.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(success, success, success, error, error)
        )

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            return_value=json.loads(load_fixture("wifi_detail_all_with_game_data.json"))
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH_NAME, updater
        )

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)

        assert entry.disabled_by is None
        assert state.state == "max"
        assert state.name == ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH_NAME
        assert state.attributes["icon"] == "mdi:wifi-strength-4"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["options"] == ATTR_SELECT_SIGNAL_STRENGTH_OPTIONS
        assert entry.entity_category == EntityCategory.CONFIG

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "max"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_strength_5_0_game_wifi_data(hass: HomeAssistant) -> None:
    """Test update strength 5.0 game.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_with_game_data.json"))

        def change_wifi_data() -> dict:
            return json.loads(
                load_fixture("wifi_detail_all_with_game_change_data.json")
            )

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            side_effect=MultipleSideEffect(
                success_wifi_data,
                success_wifi_data,
                success_wifi_data,
                change_wifi_data,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_5_0_GAME_DATA) == {
            "ssid": "**REDACTED**",
            "pwd": "**REDACTED**",
            "encryption": "psk2",
            "channel": 48,
            "bandwidth": "0",
            "txpwr": "max",
            "hidden": "0",
            "on": "1",
            "txbf": "3",
        }

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH_NAME, updater
        )

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)

        assert entry.disabled_by is None

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_5_0_GAME_DATA) == {
            "ssid": "**REDACTED**",
            "pwd": "**REDACTED**",
            "encryption": "psk2",
            "channel": 48,
            "bandwidth": "0",
            "txpwr": "min",
            "hidden": "0",
            "on": "1",
            "txbf": "3",
        }


async def test_update_strength_5_0_game_change_strength(hass: HomeAssistant) -> None:
    """Test update strength 5.0 game.

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
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            return_value=json.loads(load_fixture("wifi_detail_all_with_game_data.json"))
        )

        def success_set_wifi(data: dict) -> dict:
            return {"code": 0}

        def error_set_wifi(data: dict) -> None:
            raise LuciTokenException

        mock_luci_client.return_value.set_wifi = AsyncMock(
            side_effect=MultipleSideEffect(
                success_set_wifi,
                error_set_wifi,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(
            ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH_NAME, updater
        )

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

        registry.async_update_entity(entity_id=unique_id, disabled_by=None)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        entry = registry.async_get(unique_id)

        assert entry.disabled_by is None

        state = hass.states.get(unique_id)
        assert state.attributes["icon"] == "mdi:wifi-strength-4"

        _prev_calls: int = len(mock_luci_client.mock_calls)

        assert await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: [unique_id], ATTR_OPTION: "min"},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == "min"
        assert state.attributes["icon"] == "mdi:wifi-strength-1"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 1

        assert await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: [unique_id], ATTR_OPTION: "mid"},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == "mid"
        assert state.attributes["icon"] == "mdi:wifi-strength-2"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 2


def _generate_id(code: str, updater: UPDATER) -> str:
    """Generate unique id

    :param code: str
    :param updater: UPDATER
    :return str
    """

    return generate_entity_id(
        SELECT_ENTITY_ID_FORMAT,
        updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip),
        code,
    )
