"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import json
import logging
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.switch import ENTITY_ID_FORMAT as SWITCH_ENTITY_ID_FORMAT
from homeassistant.components.switch import SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    load_fixture,
)

from custom_components.miwifi.const import (
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_SWITCH_WIFI_2_4_NAME,
    ATTR_SWITCH_WIFI_5_0_GAME_NAME,
    ATTR_SWITCH_WIFI_5_0_NAME,
    ATTR_SWITCH_WIFI_GUEST_NAME,
    ATTR_WIFI_2_4_DATA,
    ATTR_WIFI_5_0_DATA,
    ATTR_WIFI_5_0_GAME_DATA,
    ATTR_WIFI_GUEST_DATA,
    ATTRIBUTION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    UPDATER,
)
from custom_components.miwifi.exceptions import LuciConnectionError, LuciRequestError
from custom_components.miwifi.helper import generate_entity_id
from custom_components.miwifi.updater import LuciUpdater
from tests.setup import MultipleSideEffect, async_mock_luci_client, async_setup

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


@pytest.mark.asyncio
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

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_2_4_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SWITCH_WIFI_5_0_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SWITCH_WIFI_5_0_GAME_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None

        unique_id = _generate_id(ATTR_SWITCH_WIFI_GUEST_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None


@pytest.mark.asyncio
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
        mock_luci_client.return_value.wifi_diag_detail_all = AsyncMock(
            return_value=json.loads(
                load_fixture("wifi_diag_detail_all_with_game_data.json")
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_2_4_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SWITCH_WIFI_5_0_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SWITCH_WIFI_5_0_GAME_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SWITCH_WIFI_GUEST_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None


@pytest.mark.asyncio
async def test_init_without_guest(hass: HomeAssistant) -> None:
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
        mock_luci_client.return_value.wifi_diag_detail_all = AsyncMock(return_value={})

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_2_4_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SWITCH_WIFI_5_0_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SWITCH_WIFI_5_0_GAME_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SWITCH_WIFI_GUEST_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None


@pytest.mark.asyncio
async def test_init_with_error(hass: HomeAssistant) -> None:
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
            side_effect=LuciConnectionError
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_2_4_NAME, updater)
        states: State | None = hass.states.get(unique_id)
        assert states is not None
        assert states.state == STATE_UNAVAILABLE
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SWITCH_WIFI_5_0_NAME, updater)
        states = hass.states.get(unique_id)
        assert states is not None
        assert states.state == STATE_UNAVAILABLE
        assert registry.async_get(unique_id) is not None


@pytest.mark.asyncio
async def test_init_bsd(
    hass: HomeAssistant,
) -> None:
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

        def bsd_off() -> dict:
            return json.loads(load_fixture("wifi_detail_all_with_game_data.json"))

        def bsd_on() -> dict:
            return json.loads(
                load_fixture("wifi_detail_all_with_game_and_bsd_data.json")
            )

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            side_effect=MultipleSideEffect(bsd_off, bsd_on)
        )
        mock_luci_client.return_value.wifi_diag_detail_all = AsyncMock(
            return_value=json.loads(
                load_fixture("wifi_diag_detail_all_with_game_data.json")
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_2_4_NAME, updater)
        entry = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["friendly_name"] == ATTR_SWITCH_WIFI_2_4_NAME
        assert entry.original_name == ATTR_SWITCH_WIFI_2_4_NAME

        unique_id = _generate_id(ATTR_SWITCH_WIFI_5_0_NAME, updater)
        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["friendly_name"] == ATTR_SWITCH_WIFI_5_0_NAME
        assert entry.original_name == ATTR_SWITCH_WIFI_5_0_NAME

        unique_id = _generate_id(ATTR_SWITCH_WIFI_5_0_GAME_NAME, updater)
        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["friendly_name"] == ATTR_SWITCH_WIFI_5_0_GAME_NAME
        assert entry.original_name == ATTR_SWITCH_WIFI_5_0_GAME_NAME

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        unique_id = _generate_id(ATTR_SWITCH_WIFI_2_4_NAME, updater)
        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["friendly_name"] == ATTR_SWITCH_WIFI_2_4_NAME
        assert entry.original_name == ATTR_SWITCH_WIFI_2_4_NAME

        unique_id = _generate_id(ATTR_SWITCH_WIFI_5_0_NAME, updater)
        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE
        assert state.attributes["friendly_name"] == ATTR_SWITCH_WIFI_5_0_NAME
        assert entry.original_name == ATTR_SWITCH_WIFI_5_0_NAME

        unique_id = _generate_id(ATTR_SWITCH_WIFI_5_0_GAME_NAME, updater)
        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE
        assert state.attributes["friendly_name"] == ATTR_SWITCH_WIFI_5_0_GAME_NAME
        assert entry.original_name == ATTR_SWITCH_WIFI_5_0_GAME_NAME


@pytest.mark.asyncio
async def test_update_2_4(hass: HomeAssistant) -> None:
    """Test update 2.4.

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
            raise LuciRequestError

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(success, error, error)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_2_4_NAME, updater)

        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)

        assert entry.disabled_by is None
        assert state.state == STATE_ON
        assert state.name == ATTR_SWITCH_WIFI_2_4_NAME
        assert state.attributes["icon"] == "mdi:wifi"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category == EntityCategory.CONFIG

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


@pytest.mark.asyncio
async def test_update_2_4_wifi_data(hass: HomeAssistant) -> None:
    """Test update 2.4.

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
            raise LuciRequestError

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(success, error)
        )

        def success_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_data.json"))

        def change_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_change_data.json"))

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            side_effect=MultipleSideEffect(
                success_wifi_data,
                change_wifi_data,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

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

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

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


@pytest.mark.asyncio
async def test_update_2_4_turn(hass: HomeAssistant) -> None:
    """Test update 2.4.

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
            raise LuciRequestError

        mock_luci_client.return_value.set_wifi = AsyncMock(
            side_effect=MultipleSideEffect(
                success_set_wifi,
                success_set_wifi,
                error_set_wifi,
                error_set_wifi,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_2_4_NAME, updater)

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON

        _prev_calls: int = len(mock_luci_client.mock_calls)

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.attributes["icon"] == "mdi:wifi-off"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 1

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["icon"] == "mdi:wifi"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 2

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.attributes["icon"] == "mdi:wifi-off"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 3

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["icon"] == "mdi:wifi"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 4


@pytest.mark.asyncio
async def test_update_5_0(hass: HomeAssistant) -> None:
    """Test update 5.0.

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
            raise LuciRequestError

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(success, error, error)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_5_0_NAME, updater)

        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)

        assert entry.disabled_by is None
        assert state.state == STATE_ON
        assert state.name == ATTR_SWITCH_WIFI_5_0_NAME
        assert state.attributes["icon"] == "mdi:wifi"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category == EntityCategory.CONFIG

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


@pytest.mark.asyncio
async def test_update_5_0_wifi_data(hass: HomeAssistant) -> None:
    """Test update 5.0.

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
            raise LuciRequestError

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(success, error)
        )

        def success_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_data.json"))

        def change_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_change_data.json"))

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            side_effect=MultipleSideEffect(
                success_wifi_data,
                change_wifi_data,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_5_0_DATA) == {
            "bandwidth": "0",
            "channel": 149,
            "encryption": "psk2",
            "hidden": "0",
            "on": "1",
            "pwd": "**REDACTED**",
            "ssid": "**REDACTED**",
            "txbf": "3",
            "txpwr": "max",
        }

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_5_0_DATA) == {
            "bandwidth": "0",
            "channel": 149,
            "encryption": "psk2",
            "hidden": "0",
            "on": "1",
            "pwd": "**REDACTED**",
            "ssid": "**REDACTED**",
            "txbf": "3",
            "txpwr": "min",
        }


@pytest.mark.asyncio
async def test_update_5_0_turn(hass: HomeAssistant) -> None:
    """Test update 5.0.

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
            raise LuciRequestError

        mock_luci_client.return_value.set_wifi = AsyncMock(
            side_effect=MultipleSideEffect(
                success_set_wifi,
                success_set_wifi,
                error_set_wifi,
                error_set_wifi,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_5_0_NAME, updater)

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON

        _prev_calls: int = len(mock_luci_client.mock_calls)

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.attributes["icon"] == "mdi:wifi-off"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 1

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["icon"] == "mdi:wifi"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 2

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.attributes["icon"] == "mdi:wifi-off"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 3

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["icon"] == "mdi:wifi"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 4


@pytest.mark.asyncio
async def test_update_5_0_game(hass: HomeAssistant) -> None:
    """Test update 5.0 game.

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
        mock_luci_client.return_value.wifi_diag_detail_all = AsyncMock(
            return_value=json.loads(
                load_fixture("wifi_diag_detail_all_with_game_data.json")
            )
        )

        def success() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def error() -> None:
            raise LuciRequestError

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(success, error, error)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_5_0_GAME_NAME, updater)

        entry = registry.async_get(unique_id)
        state = hass.states.get(unique_id)

        assert entry.disabled_by is None
        assert state.state == STATE_ON
        assert state.name == ATTR_SWITCH_WIFI_5_0_GAME_NAME
        assert state.attributes["icon"] == "mdi:wifi"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category == EntityCategory.CONFIG

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


@pytest.mark.asyncio
async def test_update_5_0_game_wifi_data(hass: HomeAssistant) -> None:
    """Test update 5.0.

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

        mock_luci_client.return_value.wifi_diag_detail_all = AsyncMock(
            return_value=json.loads(
                load_fixture("wifi_diag_detail_all_with_game_data.json")
            )
        )

        def success() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def error() -> None:
            raise LuciRequestError

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(success, error)
        )

        def success_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_detail_all_with_game_data.json"))

        def change_wifi_data() -> dict:
            return json.loads(
                load_fixture("wifi_detail_all_with_game_change_data.json")
            )

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            side_effect=MultipleSideEffect(
                success_wifi_data,
                change_wifi_data,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_5_0_GAME_DATA) == {
            "bandwidth": "0",
            "channel": 48,
            "encryption": "psk2",
            "hidden": "0",
            "on": "1",
            "pwd": "**REDACTED**",
            "ssid": "**REDACTED**",
            "txbf": "3",
            "txpwr": "max",
        }

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_5_0_GAME_DATA) == {
            "bandwidth": "0",
            "channel": 48,
            "encryption": "psk2",
            "hidden": "0",
            "on": "1",
            "pwd": "**REDACTED**",
            "ssid": "**REDACTED**",
            "txbf": "3",
            "txpwr": "min",
        }


@pytest.mark.asyncio
async def test_update_5_0_game_turn(hass: HomeAssistant) -> None:
    """Test update 5.0 game.

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
        mock_luci_client.return_value.wifi_diag_detail_all = AsyncMock(
            return_value=json.loads(
                load_fixture("wifi_diag_detail_all_with_game_data.json")
            )
        )

        def success_set_wifi(data: dict) -> dict:
            return {"code": 0}

        def error_set_wifi(data: dict) -> None:
            raise LuciRequestError

        mock_luci_client.return_value.set_wifi = AsyncMock(
            side_effect=MultipleSideEffect(
                success_set_wifi,
                success_set_wifi,
                error_set_wifi,
                error_set_wifi,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_5_0_GAME_NAME, updater)

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON

        _prev_calls: int = len(mock_luci_client.mock_calls)

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.attributes["icon"] == "mdi:wifi-off"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 1

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["icon"] == "mdi:wifi"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 2

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.attributes["icon"] == "mdi:wifi-off"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 3

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["icon"] == "mdi:wifi"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 4


@pytest.mark.asyncio
async def test_update_guest(hass: HomeAssistant) -> None:
    """Test update guest.

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
            raise LuciRequestError

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

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_GUEST_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry is not None
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

        updater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert entry.disabled_by is None
        assert state.state == STATE_OFF
        assert state.name == ATTR_SWITCH_WIFI_GUEST_NAME
        assert state.attributes["icon"] == "mdi:wifi-off"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category == EntityCategory.CONFIG

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


@pytest.mark.asyncio
async def test_update_guest_wifi_data(hass: HomeAssistant) -> None:
    """Test update guest.

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
            return json.loads(load_fixture("wifi_diag_detail_all_data.json"))

        def change_wifi_data() -> dict:
            return json.loads(load_fixture("wifi_diag_detail_all_change_data.json"))

        mock_luci_client.return_value.wifi_diag_detail_all = AsyncMock(
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
        assert updater.data.get(ATTR_WIFI_GUEST_DATA) == {
            "encryption": "none",
            "on": 0,
            "pwd": "**REDACTED**",
            "ssid": "**REDACTED**",
        }

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_GUEST_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry is not None
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

        updater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success
        assert updater.data.get(ATTR_WIFI_GUEST_DATA) == {
            "encryption": "none",
            "on": 0,
            "pwd": "**NEW_REDACTED**",
            "ssid": "**REDACTED**",
        }


@pytest.mark.asyncio
async def test_update_guest_turn(hass: HomeAssistant) -> None:
    """Test update guest.

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
            raise LuciRequestError

        mock_luci_client.return_value.set_guest_wifi = AsyncMock(
            side_effect=MultipleSideEffect(
                success_set_wifi,
                success_set_wifi,
                error_set_wifi,
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

        unique_id: str = _generate_id(ATTR_SWITCH_WIFI_GUEST_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state is None
        assert entry is not None
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
        assert state.state == STATE_OFF

        _prev_calls: int = len(mock_luci_client.mock_calls)

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["icon"] == "mdi:wifi-lock-open"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 1

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.attributes["icon"] == "mdi:wifi-off"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 2

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["icon"] == "mdi:wifi-lock-open"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 3

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.attributes["icon"] == "mdi:wifi-off"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 4

#
# @pytest.mark.asyncio
# async def test_update_qos_turn(hass: HomeAssistant) -> None:
#     """Test update qos.
#
#     :param hass: HomeAssistant
#     """
#
#     with patch(
#             "custom_components.miwifi.updater.LuciClient"
#     ) as mock_luci_client, patch(
#         "custom_components.miwifi.async_start_discovery", return_value=None
#     ), patch(
#         "custom_components.miwifi.device_tracker.socket.socket"
#     ) as mock_socket, patch(
#         "custom_components.miwifi.updater.asyncio.sleep", return_value=None
#     ):
#         await async_mock_luci_client(mock_luci_client)
#
#         mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)
#
#         def success_set_qos(data: dict) -> dict:
#             return {"code": 0}
#
#         def error_set_qos(data: dict) -> None:
#             raise LuciRequestError
#
#         mock_luci_client.return_value.qos_toggle = AsyncMock(
#             side_effect=MultipleSideEffect(
#                 success_set_qos,
#                 success_set_qos,
#                 error_set_qos,
#                 error_set_qos,
#             )
#         )
#
#         setup_data: list = await async_setup(hass)
#
#         config_entry: MockConfigEntry = setup_data[1]
#
#         assert await hass.config_entries.async_setup(config_entry.entry_id)
#         await hass.async_block_till_done()
#
#         updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
#         registry = er.async_get(hass)
#
#         assert updater.last_update_success
#
#         unique_id: str = _generate_id(ATTR_SWITCH_WIFI_GUEST_NAME, updater)
#
#         entry: er.RegistryEntry | None = registry.async_get(unique_id)
#         state: State = hass.states.get(unique_id)
#         assert state is None
#         assert entry is not None
#         assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
#
#         registry.async_update_entity(entity_id=unique_id, disabled_by=None)
#         await hass.async_block_till_done()
#
#         async_fire_time_changed(
#             hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
#         )
#         await hass.async_block_till_done()
#
#         async_fire_time_changed(
#             hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
#         )
#         await hass.async_block_till_done()
#
#         entry = registry.async_get(unique_id)
#
#         assert entry.disabled_by is None
#
#         state = hass.states.get(unique_id)
#         assert state.state == STATE_OFF
#
#         _prev_calls: int = len(mock_luci_client.mock_calls)
#
#         assert await hass.services.async_call(
#             SWITCH_DOMAIN,
#             SERVICE_TURN_ON,
#             {ATTR_ENTITY_ID: [unique_id]},
#             blocking=True,
#             limit=None,
#         )
#
#         state = hass.states.get(unique_id)
#         assert state.state == STATE_ON
#         assert state.attributes["icon"] == "mdi:wifi-lock-open"
#         assert len(mock_luci_client.mock_calls) == _prev_calls + 1
#
#         assert await hass.services.async_call(
#             SWITCH_DOMAIN,
#             SERVICE_TURN_OFF,
#             {ATTR_ENTITY_ID: [unique_id]},
#             blocking=True,
#             limit=None,
#         )
#
#         state = hass.states.get(unique_id)
#         assert state.state == STATE_OFF
#         assert state.attributes["icon"] == "mdi:wifi-off"
#         assert len(mock_luci_client.mock_calls) == _prev_calls + 2
#
#         assert await hass.services.async_call(
#             SWITCH_DOMAIN,
#             SERVICE_TURN_ON,
#             {ATTR_ENTITY_ID: [unique_id]},
#             blocking=True,
#             limit=None,
#         )
#
#         state = hass.states.get(unique_id)
#         assert state.state == STATE_ON
#         assert state.attributes["icon"] == "mdi:wifi-lock-open"
#         assert len(mock_luci_client.mock_calls) == _prev_calls + 3
#
#         assert await hass.services.async_call(
#             SWITCH_DOMAIN,
#             SERVICE_TURN_OFF,
#             {ATTR_ENTITY_ID: [unique_id]},
#             blocking=True,
#             limit=None,
#         )
#
#         state = hass.states.get(unique_id)
#         assert state.state == STATE_OFF
#         assert state.attributes["icon"] == "mdi:wifi-off"
#         assert len(mock_luci_client.mock_calls) == _prev_calls + 4


def _generate_id(code: str, updater: LuciUpdater) -> str:
    """Generate unique id

    :param code: str
    :param updater: LuciUpdater
    :return str
    """

    return generate_entity_id(
        SWITCH_ENTITY_ID_FORMAT,
        updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip),
        code,
    )
