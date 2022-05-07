"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

from datetime import timedelta
import logging
from unittest.mock import AsyncMock, patch
import json
import pytest
from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT as SENSOR_ENTITY_ID_FORMAT,
)
from homeassistant.const import (
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
    ATTR_SENSOR_UPTIME_NAME,
    ATTR_SENSOR_MEMORY_USAGE_NAME,
    ATTR_SENSOR_MEMORY_TOTAL_NAME,
    ATTR_SENSOR_TEMPERATURE_NAME,
    ATTR_SENSOR_MODE_NAME,
    ATTR_SENSOR_AP_SIGNAL_NAME,
    ATTR_SENSOR_WAN_DOWNLOAD_SPEED_NAME,
    ATTR_SENSOR_WAN_UPLOAD_SPEED_NAME,
    ATTR_SENSOR_DEVICES_NAME,
    ATTR_SENSOR_DEVICES_LAN_NAME,
    ATTR_SENSOR_DEVICES_GUEST_NAME,
    ATTR_SENSOR_DEVICES_2_4_NAME,
    ATTR_SENSOR_DEVICES_5_0_NAME,
    ATTR_SENSOR_DEVICES_5_0_GAME_NAME,
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

        unique_id: str = _generate_id(ATTR_SENSOR_UPTIME_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_MEMORY_USAGE_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_MEMORY_TOTAL_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_TEMPERATURE_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None

        unique_id = _generate_id(ATTR_SENSOR_MODE_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_AP_SIGNAL_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None

        unique_id = _generate_id(ATTR_SENSOR_WAN_DOWNLOAD_SPEED_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_WAN_UPLOAD_SPEED_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_LAN_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_2_4_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_5_0_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_GUEST_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_5_0_GAME_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None


async def test_init_with_game(
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

        unique_id: str = _generate_id(ATTR_SENSOR_UPTIME_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_MEMORY_USAGE_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_MEMORY_TOTAL_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_TEMPERATURE_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None

        unique_id = _generate_id(ATTR_SENSOR_MODE_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_AP_SIGNAL_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None

        unique_id = _generate_id(ATTR_SENSOR_WAN_DOWNLOAD_SPEED_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_WAN_UPLOAD_SPEED_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_LAN_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_2_4_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_5_0_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_GUEST_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_5_0_GAME_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None


async def test_init_without_zero(
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

        mock_luci_client.return_value.status = AsyncMock(
            return_value=json.loads(load_fixture("status_with_temperature_data.json"))
        )
        mock_luci_client.return_value.mode = AsyncMock(
            return_value=json.loads(load_fixture("mode_repeater_data.json"))
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_UPTIME_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_MEMORY_USAGE_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_MEMORY_TOTAL_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_TEMPERATURE_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_MODE_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_AP_SIGNAL_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_WAN_DOWNLOAD_SPEED_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_WAN_UPLOAD_SPEED_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_LAN_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_2_4_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_5_0_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_GUEST_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_5_0_GAME_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None


async def test_init_without_wan(
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

        mock_luci_client.return_value.wan_info = AsyncMock(
            return_value=json.loads(load_fixture("wan_info_wan_off_data.json"))
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_UPTIME_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_MEMORY_USAGE_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_MEMORY_TOTAL_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_TEMPERATURE_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None

        unique_id = _generate_id(ATTR_SENSOR_MODE_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_AP_SIGNAL_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None

        unique_id = _generate_id(ATTR_SENSOR_WAN_DOWNLOAD_SPEED_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None

        unique_id = _generate_id(ATTR_SENSOR_WAN_UPLOAD_SPEED_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_LAN_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_2_4_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_5_0_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_GUEST_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is not None

        unique_id = _generate_id(ATTR_SENSOR_DEVICES_5_0_GAME_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None


async def test_update_uptime(hass: HomeAssistant) -> None:
    """Test update uptime.

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

        def original() -> dict:
            return json.loads(load_fixture("status_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("status_change_data.json"))

        mock_luci_client.return_value.status = AsyncMock(
            side_effect=MultipleSideEffect(original, original, original, change, change)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_UPTIME_NAME, updater)

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

        assert entry.disabled_by is None
        assert state.state == "8:06:26"
        assert state.name == ATTR_SENSOR_UPTIME_NAME
        assert state.attributes["icon"] == "mdi:timer-sand"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category == EntityCategory.DIAGNOSTIC

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "0:19:46"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_memory_usage(hass: HomeAssistant) -> None:
    """Test update memory usage.

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

        def original() -> dict:
            return json.loads(load_fixture("status_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("status_change_data.json"))

        mock_luci_client.return_value.status = AsyncMock(
            side_effect=MultipleSideEffect(original, original, original, change, change)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_MEMORY_USAGE_NAME, updater)

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

        assert entry.disabled_by is None
        assert state.state == "53"
        assert state.name == ATTR_SENSOR_MEMORY_USAGE_NAME
        assert state.attributes["icon"] == "mdi:memory"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category == EntityCategory.DIAGNOSTIC

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "153"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_memory_total(hass: HomeAssistant) -> None:
    """Test update memory total.

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

        def original() -> dict:
            return json.loads(load_fixture("status_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("status_change_data.json"))

        mock_luci_client.return_value.status = AsyncMock(
            side_effect=MultipleSideEffect(original, original, original, change, change)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_MEMORY_TOTAL_NAME, updater)

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

        assert entry.disabled_by is None
        assert state.state == "256"
        assert state.name == ATTR_SENSOR_MEMORY_TOTAL_NAME
        assert state.attributes["icon"] == "mdi:memory"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category == EntityCategory.DIAGNOSTIC

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "512"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_temperature(hass: HomeAssistant) -> None:
    """Test update temperature.

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

        def original() -> dict:
            return json.loads(load_fixture("status_with_temperature_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("status_change_data.json"))

        mock_luci_client.return_value.status = AsyncMock(
            side_effect=MultipleSideEffect(original, original, original, change, change)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_TEMPERATURE_NAME, updater)

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

        assert entry.disabled_by is None
        assert state.state == "10.0"
        assert state.name == ATTR_SENSOR_TEMPERATURE_NAME
        assert state.attributes["icon"] == "mdi:temperature-celsius"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category == EntityCategory.DIAGNOSTIC

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "60.0"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_mode(hass: HomeAssistant) -> None:
    """Test update mode.

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
            return json.loads(load_fixture("wifi_connect_devices_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.wifi_connect_devices = AsyncMock(
            side_effect=MultipleSideEffect(success, error, error)
        )

        def original() -> dict:
            return json.loads(load_fixture("mode_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("mode_repeater_data.json"))

        mock_luci_client.return_value.mode = AsyncMock(
            side_effect=MultipleSideEffect(original, change, change)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_MODE_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state.state == "default"
        assert state.name == ATTR_SENSOR_MODE_NAME
        assert state.attributes["icon"] == "mdi:transit-connection-variant"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry is not None
        assert entry.entity_category == EntityCategory.DIAGNOSTIC

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "repeater"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_ap_signal(hass: HomeAssistant) -> None:
    """Test update ap signal.

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
            return json.loads(load_fixture("new_status_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.new_status = AsyncMock(
            side_effect=MultipleSideEffect(success, error, error)
        )

        mock_luci_client.return_value.mode = AsyncMock(
            return_value=json.loads(load_fixture("mode_repeater_data.json"))
        )

        def original() -> dict:
            return json.loads(load_fixture("wifi_ap_signal_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("wifi_ap_signal_change_data.json"))

        mock_luci_client.return_value.wifi_ap_signal = AsyncMock(
            side_effect=MultipleSideEffect(original, change, change)
        )

        setup_data: list = await async_setup(hass, is_force=True)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_AP_SIGNAL_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state.state == "27"
        assert state.name == ATTR_SENSOR_AP_SIGNAL_NAME
        assert state.attributes["icon"] == "mdi:wifi-arrow-left-right"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry is not None
        assert entry.entity_category == EntityCategory.DIAGNOSTIC

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "98"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_download_speed(hass: HomeAssistant) -> None:
    """Test update download speed.

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
            return json.loads(load_fixture("wifi_connect_devices_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.wifi_connect_devices = AsyncMock(
            side_effect=MultipleSideEffect(success, error, error)
        )

        def original() -> dict:
            return json.loads(load_fixture("status_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("status_change_data.json"))

        mock_luci_client.return_value.status = AsyncMock(
            side_effect=MultipleSideEffect(original, change, change)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_WAN_DOWNLOAD_SPEED_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state.state == "225064.0"
        assert state.name == ATTR_SENSOR_WAN_DOWNLOAD_SPEED_NAME
        assert state.attributes["icon"] == "mdi:speedometer"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry is not None
        assert entry.entity_category == EntityCategory.DIAGNOSTIC

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "5064.0"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_upload_speed(hass: HomeAssistant) -> None:
    """Test update upload speed.

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
            return json.loads(load_fixture("wifi_connect_devices_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.wifi_connect_devices = AsyncMock(
            side_effect=MultipleSideEffect(success, error, error)
        )

        def original() -> dict:
            return json.loads(load_fixture("status_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("status_change_data.json"))

        mock_luci_client.return_value.status = AsyncMock(
            side_effect=MultipleSideEffect(original, change, change)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_WAN_UPLOAD_SPEED_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state.state == "19276.0"
        assert state.name == ATTR_SENSOR_WAN_UPLOAD_SPEED_NAME
        assert state.attributes["icon"] == "mdi:speedometer"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry is not None
        assert entry.entity_category == EntityCategory.DIAGNOSTIC

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "119276.0"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_devices(hass: HomeAssistant) -> None:
    """Test update devices.

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
            return json.loads(load_fixture("wifi_connect_devices_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.wifi_connect_devices = AsyncMock(
            side_effect=MultipleSideEffect(success, success, error, error)
        )

        def original() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("device_list_change_lan_data.json"))

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(original, change)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_DEVICES_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state.state == "3"
        assert state.name == ATTR_SENSOR_DEVICES_NAME
        assert state.attributes["icon"] == "mdi:counter"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry is not None
        assert entry.entity_category is None

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
        assert state.state == "0"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_devices_lan(hass: HomeAssistant) -> None:
    """Test update devices lan.

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
            return json.loads(load_fixture("wifi_connect_devices_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.wifi_connect_devices = AsyncMock(
            side_effect=MultipleSideEffect(
                success, success, success, success, error, error
            )
        )

        def original() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("device_list_change_lan_data.json"))

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(original, original, original, change)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_DEVICES_LAN_NAME, updater)

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

        assert entry.disabled_by is None
        assert state.state == "1"
        assert state.name == ATTR_SENSOR_DEVICES_LAN_NAME
        assert state.attributes["icon"] == "mdi:counter"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category is None

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "0"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "0"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_devices_2_4(hass: HomeAssistant) -> None:
    """Test update devices 2.4.

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
            return json.loads(load_fixture("wifi_connect_devices_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.wifi_connect_devices = AsyncMock(
            side_effect=MultipleSideEffect(
                success, success, success, success, error, error
            )
        )

        def original() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("device_list_change_2_4_data.json"))

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(original, original, original, change)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_DEVICES_2_4_NAME, updater)

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

        assert entry.disabled_by is None
        assert state.state == "1"
        assert state.name == ATTR_SENSOR_DEVICES_2_4_NAME
        assert state.attributes["icon"] == "mdi:counter"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category is None

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
        assert state.state == "0"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_devices_5_0(hass: HomeAssistant) -> None:
    """Test update devices 5.0.

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
            return json.loads(load_fixture("wifi_connect_devices_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.wifi_connect_devices = AsyncMock(
            side_effect=MultipleSideEffect(
                success, success, success, success, error, error
            )
        )

        def original() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("device_list_change_5_0_data.json"))

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(original, original, original, change)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_DEVICES_5_0_NAME, updater)

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

        assert entry.disabled_by is None
        assert state.state == "1"
        assert state.name == ATTR_SENSOR_DEVICES_5_0_NAME
        assert state.attributes["icon"] == "mdi:counter"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category is None

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
        assert state.state == "0"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_devices_guest(hass: HomeAssistant) -> None:
    """Test update devices guest.

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
            return json.loads(load_fixture("wifi_connect_devices_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.wifi_connect_devices = AsyncMock(
            side_effect=MultipleSideEffect(
                success, success, success, success, error, error
            )
        )

        def original() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("device_list_change_guest_data.json"))

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(original, original, original, change)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_DEVICES_GUEST_NAME, updater)

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

        assert entry.disabled_by is None
        assert state.state == "0"
        assert state.name == ATTR_SENSOR_DEVICES_GUEST_NAME
        assert state.attributes["icon"] == "mdi:counter"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category is None

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "1"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "0"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


async def test_update_devices_5_0_game(hass: HomeAssistant) -> None:
    """Test update devices 5.0 game.

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

        def success() -> dict:
            return json.loads(load_fixture("wifi_connect_devices_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.wifi_connect_devices = AsyncMock(
            side_effect=MultipleSideEffect(
                success, success, success, success, error, error
            )
        )

        def original() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def change() -> dict:
            return json.loads(load_fixture("device_list_change_5_0_game_data.json"))

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(original, original, original, change)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_SENSOR_DEVICES_5_0_GAME_NAME, updater)

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

        assert entry.disabled_by is None
        assert state.state == "0"
        assert state.name == ATTR_SENSOR_DEVICES_5_0_GAME_NAME
        assert state.attributes["icon"] == "mdi:counter"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category is None

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "1"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == "0"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


def _generate_id(code: str, updater: LuciUpdater) -> str:
    """Generate unique id

    :param code: str
    :param updater: LuciUpdater
    :return str
    """

    return generate_entity_id(
        SENSOR_ENTITY_ID_FORMAT,
        updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip),
        code,
    )
