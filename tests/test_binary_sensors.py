"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

from datetime import timedelta
import logging
from unittest.mock import AsyncMock, patch
import json
import pytest
from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT as BINARY_SENSOR_ENTITY_ID_FORMAT,
)
from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
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
    ATTR_STATE_NAME,
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_BINARY_SENSOR_WAN_STATE_NAME,
    ATTR_BINARY_SENSOR_DUAL_BAND_NAME,
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

        assert updater.last_update_success

        state: State = hass.states.get(_generate_id(ATTR_STATE_NAME, updater))
        assert state.state == STATE_ON
        assert state.name == ATTR_STATE_NAME
        assert state.attributes["icon"] == "mdi:router-wireless"
        assert state.attributes["attribution"] == ATTRIBUTION

        wan_state: State = hass.states.get(
            _generate_id(ATTR_BINARY_SENSOR_WAN_STATE_NAME, updater)
        )
        assert wan_state.state == STATE_ON
        assert wan_state.name == ATTR_BINARY_SENSOR_WAN_STATE_NAME
        assert wan_state.attributes["icon"] == "mdi:wan"
        assert wan_state.attributes["attribution"] == ATTRIBUTION

        dual_band_state: State | None = hass.states.get(
            _generate_id(ATTR_BINARY_SENSOR_DUAL_BAND_NAME, updater)
        )
        assert dual_band_state is None


async def test_update_state(hass: HomeAssistant) -> None:
    """Test update state.

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
            return json.loads(load_fixture("status_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.status = AsyncMock(
            side_effect=MultipleSideEffect(success, error, error)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_STATE_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.name == ATTR_STATE_NAME
        assert state.attributes["icon"] == "mdi:router-wireless"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry is not None
        assert entry.entity_category == EntityCategory.DIAGNOSTIC

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["icon"] == "mdi:router-wireless"

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.attributes["icon"] == "mdi:router-wireless-off"


async def test_update_wan_state(hass: HomeAssistant) -> None:
    """Test update wan state.

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
            side_effect=MultipleSideEffect(success, error, error)
        )

        def _on() -> dict:
            return json.loads(load_fixture("wan_info_data.json"))

        def _off() -> dict:
            return json.loads(load_fixture("wan_info_wan_off_data.json"))

        mock_luci_client.return_value.wan_info = AsyncMock(
            side_effect=MultipleSideEffect(_on, _off, _off)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_BINARY_SENSOR_WAN_STATE_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.name == ATTR_BINARY_SENSOR_WAN_STATE_NAME
        assert state.attributes["icon"] == "mdi:wan"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry is not None
        assert entry.entity_category == EntityCategory.DIAGNOSTIC

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


async def test_update_dual_band(hass: HomeAssistant) -> None:
    """Test update dual_band.

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

        def _off() -> dict:
            return json.loads(load_fixture("wifi_detail_all_data.json"))

        def _on() -> dict:
            return json.loads(load_fixture("wifi_detail_all_bsd_on_data.json"))

        mock_luci_client.return_value.wifi_detail_all = AsyncMock(
            side_effect=MultipleSideEffect(_off, _off, _off, _on, _on)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_BINARY_SENSOR_DUAL_BAND_NAME, updater)

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
        assert state.state == STATE_OFF
        assert state.name == ATTR_BINARY_SENSOR_DUAL_BAND_NAME
        assert state.attributes["icon"] == "mdi:wifi-plus"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry.entity_category == EntityCategory.DIAGNOSTIC

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON

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
        BINARY_SENSOR_ENTITY_ID_FORMAT,
        updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip),
        code,
    )
