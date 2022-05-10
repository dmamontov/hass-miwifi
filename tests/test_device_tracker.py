"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import json
import logging
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.device_tracker import (
    ENTITY_ID_FORMAT as DEVICE_TRACKER_ENTITY_ID_FORMAT,
)
from homeassistant.components.device_tracker import SOURCE_TYPE_ROUTER
from homeassistant.const import STATE_HOME, STATE_NOT_HOME, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    load_fixture,
)

from custom_components.miwifi.const import (
    ATTRIBUTION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MANUFACTURERS,
    UPDATER,
)
from custom_components.miwifi.enum import Connection
from custom_components.miwifi.helper import generate_entity_id
from custom_components.miwifi.updater import LuciUpdater
from tests.setup import MultipleSideEffect, async_mock_luci_client, async_setup

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
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        state: State = hass.states.get(_generate_id("00:00:00:00:00:01"))
        assert state.state == STATE_HOME
        assert state.name == "Device 1"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.2"
        assert state.attributes["mac"] == "00:00:00:00:00:01"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert state.attributes["signal"] == 100
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(_generate_id("00:00:00:00:00:02"))
        assert state.state == STATE_HOME
        assert state.name == "Device 2"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.3"
        assert state.attributes["mac"] == "00:00:00:00:00:02"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.WIFI_5_0.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert state.attributes["signal"] == 100
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(_generate_id("00:00:00:00:00:03"))
        assert state.state == STATE_HOME
        assert state.name == "Device 3"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.4"
        assert state.attributes["mac"] == "00:00:00:00:00:03"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert len(state.attributes["signal"]) == 0
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION


async def test_init_with_restore(hass: HomeAssistant) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket, patch(
        "custom_components.miwifi.helper.Store"
    ) as mock_store:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        mock_store.return_value.async_load = AsyncMock(
            return_value=json.loads(load_fixture("store_data.json"))
        )
        mock_store.return_value.async_save = AsyncMock(return_value=None)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        state: State = hass.states.get(_generate_id("00:00:00:00:00:01"))
        assert state.state == STATE_HOME
        assert state.name == "Device 1"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.2"
        assert state.attributes["mac"] == "00:00:00:00:00:01"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert state.attributes["signal"] == 100
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(_generate_id("00:00:00:00:00:02"))
        assert state.state == STATE_HOME
        assert state.name == "Device 2"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.3"
        assert state.attributes["mac"] == "00:00:00:00:00:02"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.WIFI_5_0.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert state.attributes["signal"] == 100
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(_generate_id("00:00:00:00:00:03"))
        assert state.state == STATE_HOME
        assert state.name == "Device 3"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.4"
        assert state.attributes["mac"] == "00:00:00:00:00:03"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert len(state.attributes["signal"]) == 0
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(_generate_id("00:00:00:00:00:05"))
        assert state.state == STATE_NOT_HOME
        assert state.name == "Device 5"
        assert state.attributes["icon"] == "mdi:lan-disconnect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.55"
        assert state.attributes["mac"] == "00:00:00:00:00:05"
        assert state.attributes["scanner"] == DOMAIN
        assert len(state.attributes["online"]) == 0
        assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert len(state.attributes["signal"]) == 0
        assert len(state.attributes["down_speed"]) == 0
        assert len(state.attributes["up_speed"]) == 0
        assert state.attributes["attribution"] == ATTRIBUTION


async def test_init_with_parent(hass: HomeAssistant) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client_first, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket_first:
        mock_socket_first.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client_first)

        mock_luci_client_first.return_value.device_list = AsyncMock(
            return_value=json.loads(load_fixture("device_list_parent_data.json"))
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater_first: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

    assert updater_first.last_update_success

    state: State = hass.states.get(_generate_id("00:00:00:00:00:01"))
    assert state.state == STATE_HOME
    assert state.name == "Device 1"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.2"
    assert state.attributes["mac"] == "00:00:00:00:00:01"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert state.attributes["signal"] == 100
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:02"))
    assert state.state == STATE_HOME
    assert state.name == "Device 2"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.3"
    assert state.attributes["mac"] == "00:00:00:00:00:02"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_5_0.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert state.attributes["signal"] == 100
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:03"))
    assert state.state == STATE_HOME
    assert state.name == "Device 3"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.4"
    assert state.attributes["mac"] == "00:00:00:00:00:03"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:04"))
    assert state.state == STATE_HOME
    assert state.name == "Device 4 (Repeater)"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.100"
    assert state.attributes["mac"] == "00:00:00:00:00:04"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client_second, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket_second:
        mock_socket_second.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client_second)

        mock_luci_client_second.return_value.mode = AsyncMock(
            return_value=json.loads(load_fixture("mode_repeater_data.json"))
        )
        mock_luci_client_second.return_value.wifi_connect_devices = AsyncMock(
            return_value=json.loads(
                load_fixture("wifi_connect_devices_parent_data.json")
            )
        )
        mock_luci_client_second.return_value.status = AsyncMock(
            return_value=json.loads(load_fixture("status_parent_data.json"))
        )

        setup_data = await async_setup(hass, "192.168.31.100")

        config_entry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater_second: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

    assert updater_second.last_update_success

    state = hass.states.get(_generate_id("00:00:00:00:00:01"))
    assert state.state == STATE_HOME
    assert state.name == "Device 1"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.2"
    assert state.attributes["mac"] == "00:00:00:00:00:01"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
    assert state.attributes["router_mac"] == "01:00:00:00:00:00"
    assert state.attributes["signal"] == 10
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:02"))
    assert state.state == STATE_HOME
    assert state.name == "Device 2"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.3"
    assert state.attributes["mac"] == "00:00:00:00:00:02"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_5_0.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert state.attributes["signal"] == 100
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:03"))
    assert state.state == STATE_HOME
    assert state.name == "Device 3"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.4"
    assert state.attributes["mac"] == "00:00:00:00:00:03"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:04"))
    assert state.state == STATE_HOME
    assert state.name == "Device 4 (Repeater)"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.100"
    assert state.attributes["mac"] == "00:00:00:00:00:04"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION


async def test_init_with_parent_revert(hass: HomeAssistant) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client_first, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket_first:
        mock_socket_first.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client_first)

        def parent() -> dict:
            return json.loads(load_fixture("device_list_parent_data.json"))

        def revert() -> dict:
            return json.loads(load_fixture("device_list_revert_parent_data.json"))

        mock_luci_client_first.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(
                parent, parent, parent, parent, revert, revert
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater_first: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

    assert updater_first.last_update_success

    state: State = hass.states.get(_generate_id("00:00:00:00:00:01"))
    assert state.state == STATE_HOME
    assert state.name == "Device 1"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.2"
    assert state.attributes["mac"] == "00:00:00:00:00:01"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert state.attributes["signal"] == 100
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:02"))
    assert state.state == STATE_HOME
    assert state.name == "Device 2"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.3"
    assert state.attributes["mac"] == "00:00:00:00:00:02"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_5_0.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert state.attributes["signal"] == 100
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:03"))
    assert state.state == STATE_HOME
    assert state.name == "Device 3"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.4"
    assert state.attributes["mac"] == "00:00:00:00:00:03"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:04"))
    assert state.state == STATE_HOME
    assert state.name == "Device 4 (Repeater)"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.100"
    assert state.attributes["mac"] == "00:00:00:00:00:04"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client_second, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket_second:
        mock_socket_second.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client_second)

        mock_luci_client_second.return_value.mode = AsyncMock(
            return_value=json.loads(load_fixture("mode_repeater_data.json"))
        )
        mock_luci_client_second.return_value.wifi_connect_devices = AsyncMock(
            return_value=json.loads(
                load_fixture("wifi_connect_devices_parent_data.json")
            )
        )
        mock_luci_client_second.return_value.status = AsyncMock(
            return_value=json.loads(load_fixture("status_parent_data.json"))
        )

        setup_data = await async_setup(hass, "192.168.31.100")

        config_entry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater_second: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

    assert updater_second.last_update_success

    state = hass.states.get(_generate_id("00:00:00:00:00:01"))
    assert state.state == STATE_HOME
    assert state.name == "Device 1"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.2"
    assert state.attributes["mac"] == "00:00:00:00:00:01"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
    assert state.attributes["router_mac"] == "01:00:00:00:00:00"
    assert state.attributes["signal"] == 10
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:02"))
    assert state.state == STATE_HOME
    assert state.name == "Device 2"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.3"
    assert state.attributes["mac"] == "00:00:00:00:00:02"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_5_0.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert state.attributes["signal"] == 100
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:03"))
    assert state.state == STATE_HOME
    assert state.name == "Device 3"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.4"
    assert state.attributes["mac"] == "00:00:00:00:00:03"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:04"))
    assert state.state == STATE_HOME
    assert state.name == "Device 4 (Repeater)"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.100"
    assert state.attributes["mac"] == "00:00:00:00:00:04"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    async_fire_time_changed(
        hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
    )
    await hass.async_block_till_done()

    state = hass.states.get(_generate_id("00:00:00:00:00:01"))
    assert state.state == STATE_HOME
    assert state.name == "Device 1"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.2"
    assert state.attributes["mac"] == "00:00:00:00:00:01"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert state.attributes["signal"] == 100
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:02"))
    assert state.state == STATE_HOME
    assert state.name == "Device 2"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.3"
    assert state.attributes["mac"] == "00:00:00:00:00:02"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_5_0.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert state.attributes["signal"] == 100
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:03"))
    assert state.state == STATE_HOME
    assert state.name == "Device 3"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.4"
    assert state.attributes["mac"] == "00:00:00:00:00:03"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:04"))
    assert state.state == STATE_HOME
    assert state.name == "Device 4 (Repeater)"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.100"
    assert state.attributes["mac"] == "00:00:00:00:00:04"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION


async def test_init_in_force_mode(hass: HomeAssistant) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.mode = AsyncMock(
            return_value=json.loads(load_fixture("mode_repeater_data.json"))
        )

        setup_data: list = await async_setup(hass, is_force=True)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        state: State = hass.states.get(_generate_id("00:00:00:00:00:01"))
        assert state.state == STATE_HOME
        assert state.name == "00:00:00:00:00:01"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] is None
        assert state.attributes["mac"] == "00:00:00:00:00:01"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "0:00:00"
        assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert state.attributes["signal"] == 100
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(_generate_id("00:00:00:00:00:02"))
        assert state.state == STATE_HOME
        assert state.name == "00:00:00:00:00:02"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] is None
        assert state.attributes["mac"] == "00:00:00:00:00:02"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "0:00:00"
        assert state.attributes["connection"] == Connection.WIFI_5_0.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert state.attributes["signal"] == 100
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(_generate_id("00:00:00:00:00:03"))
        assert state is None


async def test_init_with_force_and_parent(hass: HomeAssistant) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client_first, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket_first:
        mock_socket_first.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client_first)

        mock_luci_client_first.return_value.device_list = AsyncMock(
            return_value=json.loads(load_fixture("device_list_parent_data.json"))
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater_first: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

    assert updater_first.last_update_success

    state: State = hass.states.get(_generate_id("00:00:00:00:00:01"))
    assert state.state == STATE_HOME
    assert state.name == "Device 1"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.2"
    assert state.attributes["mac"] == "00:00:00:00:00:01"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert state.attributes["signal"] == 100
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:02"))
    assert state.state == STATE_HOME
    assert state.name == "Device 2"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.3"
    assert state.attributes["mac"] == "00:00:00:00:00:02"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_5_0.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert state.attributes["signal"] == 100
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:03"))
    assert state.state == STATE_HOME
    assert state.name == "Device 3"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.4"
    assert state.attributes["mac"] == "00:00:00:00:00:03"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:04"))
    assert state.state == STATE_HOME
    assert state.name == "Device 4 (Repeater)"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.100"
    assert state.attributes["mac"] == "00:00:00:00:00:04"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client_second, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket_second:
        mock_socket_second.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client_second)

        mock_luci_client_second.return_value.mode = AsyncMock(
            return_value=json.loads(load_fixture("mode_repeater_data.json"))
        )
        mock_luci_client_second.return_value.wifi_connect_devices = AsyncMock(
            return_value=json.loads(
                load_fixture("wifi_connect_devices_parent_data.json")
            )
        )
        mock_luci_client_second.return_value.status = AsyncMock(
            return_value=json.loads(load_fixture("status_parent_data.json"))
        )

        setup_data = await async_setup(hass, "192.168.31.100", is_force=True)

        config_entry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater_second: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

    assert updater_second.last_update_success

    state = hass.states.get(_generate_id("00:00:00:00:00:01"))
    assert state.state == STATE_HOME
    assert state.name == "Device 1"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.2"
    assert state.attributes["mac"] == "00:00:00:00:00:01"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
    assert state.attributes["router_mac"] == "01:00:00:00:00:00"
    assert state.attributes["signal"] == 10
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:02"))
    assert state.state == STATE_HOME
    assert state.name == "Device 2"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.3"
    assert state.attributes["mac"] == "00:00:00:00:00:02"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_5_0.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert state.attributes["signal"] == 100
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:03"))
    assert state.state == STATE_HOME
    assert state.name == "Device 3"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.4"
    assert state.attributes["mac"] == "00:00:00:00:00:03"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:04"))
    assert state.state == STATE_HOME
    assert state.name == "Device 4 (Repeater)"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.100"
    assert state.attributes["mac"] == "00:00:00:00:00:04"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION


async def test_init_with_restore_without_connection(hass: HomeAssistant) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket, patch(
        "custom_components.miwifi.helper.Store"
    ) as mock_store:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        mock_store.return_value.async_load = AsyncMock(
            return_value=json.loads(
                load_fixture("store_incorrect_connection_data.json")
            )
        )
        mock_store.return_value.async_save = AsyncMock(return_value=None)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        state: State = hass.states.get(_generate_id("00:00:00:00:00:01"))
        assert state.state == STATE_HOME
        assert state.name == "Device 1"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.2"
        assert state.attributes["mac"] == "00:00:00:00:00:01"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert state.attributes["signal"] == 100
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(_generate_id("00:00:00:00:00:02"))
        assert state.state == STATE_HOME
        assert state.name == "Device 2"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.3"
        assert state.attributes["mac"] == "00:00:00:00:00:02"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.WIFI_5_0.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert state.attributes["signal"] == 100
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(_generate_id("00:00:00:00:00:03"))
        assert state.state == STATE_HOME
        assert state.name == "Device 3"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.4"
        assert state.attributes["mac"] == "00:00:00:00:00:03"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert len(state.attributes["signal"]) == 0
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(_generate_id("00:00:00:00:00:05"))
        assert state.state == STATE_NOT_HOME
        assert state.name == "Device 5"
        assert state.attributes["icon"] == "mdi:lan-disconnect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.55"
        assert state.attributes["mac"] == "00:00:00:00:00:05"
        assert state.attributes["scanner"] == DOMAIN
        assert len(state.attributes["online"]) == 0
        assert state.attributes["connection"] is None
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert len(state.attributes["signal"]) == 0
        assert len(state.attributes["down_speed"]) == 0
        assert len(state.attributes["up_speed"]) == 0
        assert state.attributes["attribution"] == ATTRIBUTION


async def test_init_with_optional_parent(hass: HomeAssistant) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client_second, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket_second:
        mock_socket_second.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client_second)

        mock_luci_client_second.return_value.mode = AsyncMock(
            return_value=json.loads(load_fixture("mode_repeater_data.json"))
        )
        mock_luci_client_second.return_value.wifi_connect_devices = AsyncMock(
            return_value=json.loads(
                load_fixture("wifi_connect_devices_parent_data.json")
            )
        )
        mock_luci_client_second.return_value.status = AsyncMock(
            return_value=json.loads(load_fixture("status_parent_data.json"))
        )

        setup_data: list = await async_setup(hass, "192.168.31.100")

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client_first, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket_first:
        mock_socket_first.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client_first)

        mock_luci_client_first.return_value.device_list = AsyncMock(
            return_value=json.loads(load_fixture("device_list_parent_data.json"))
        )

        setup_data = await async_setup(hass)

        config_entry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater_first: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

    assert updater_first.last_update_success

    state: State = hass.states.get(_generate_id("00:00:00:00:00:01"))
    assert state.state == STATE_HOME
    assert state.name == "Device 1"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.2"
    assert state.attributes["mac"] == "00:00:00:00:00:01"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
    assert state.attributes["router_mac"] == "01:00:00:00:00:00"
    assert state.attributes["signal"] == 10
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:02"))
    assert state.state == STATE_HOME
    assert state.name == "Device 2"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.3"
    assert state.attributes["mac"] == "00:00:00:00:00:02"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.WIFI_5_0.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert state.attributes["signal"] == 100
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:03"))
    assert state.state == STATE_HOME
    assert state.name == "Device 3"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.4"
    assert state.attributes["mac"] == "00:00:00:00:00:03"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    state = hass.states.get(_generate_id("00:00:00:00:00:04"))
    assert state.state == STATE_HOME
    assert state.name == "Device 4 (Repeater)"
    assert state.attributes["icon"] == "mdi:lan-connect"
    assert state.attributes["attribution"] == ATTRIBUTION
    assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
    assert state.attributes["ip"] == "192.168.31.100"
    assert state.attributes["mac"] == "00:00:00:00:00:04"
    assert state.attributes["scanner"] == DOMAIN
    assert state.attributes["online"] == "8:05:01"
    assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
    assert state.attributes["router_mac"] == "00:00:00:00:00:00"
    assert len(state.attributes["signal"]) == 0
    assert state.attributes["down_speed"] == "0 B/s"
    assert state.attributes["up_speed"] == "0 B/s"
    assert state.attributes["attribution"] == ATTRIBUTION

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        set(), {(dr.CONNECTION_NETWORK_MAC, "00:00:00:00:00:04")}
    )

    assert device.connections == {
        (dr.CONNECTION_NETWORK_MAC, "00:00:00:00:00:04"),
        (dr.CONNECTION_NETWORK_MAC, "01:00:00:00:00:00"),
    }


async def test_init_with_restore_and_remove(hass: HomeAssistant) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket, patch(
        "custom_components.miwifi.helper.Store"
    ) as mock_store:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        mock_store.return_value.async_load = AsyncMock(
            return_value=json.loads(load_fixture("store_data.json"))
        )
        mock_store.return_value.async_save = AsyncMock(return_value=None)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        updater._activity_days = 1

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        assert updater.last_update_success

        state: State = hass.states.get(_generate_id("00:00:00:00:00:01"))
        assert state.state == STATE_HOME
        assert state.name == "Device 1"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.2"
        assert state.attributes["mac"] == "00:00:00:00:00:01"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert state.attributes["signal"] == 100
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(_generate_id("00:00:00:00:00:02"))
        assert state.state == STATE_HOME
        assert state.name == "Device 2"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.3"
        assert state.attributes["mac"] == "00:00:00:00:00:02"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.WIFI_5_0.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert state.attributes["signal"] == 100
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(_generate_id("00:00:00:00:00:03"))
        assert state.state == STATE_HOME
        assert state.name == "Device 3"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.4"
        assert state.attributes["mac"] == "00:00:00:00:00:03"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.LAN.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert len(state.attributes["signal"]) == 0
        assert state.attributes["down_speed"] == "0 B/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(_generate_id("00:00:00:00:00:05"))
        assert state.state == STATE_UNAVAILABLE


async def test_init_detect_manufacturer(hass: HomeAssistant) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.device_list = AsyncMock(
            return_value=json.loads(
                load_fixture("device_list_detect_manufacturer_data.json")
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(
            set(), {(dr.CONNECTION_NETWORK_MAC, "CC:50:E3:96:29:78")}
        )

        device_registry.async_update_device(device.id, manufacturer=None)

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state: State = hass.states.get(_generate_id("CC:50:E3:96:29:78"))
        assert state.state == STATE_HOME
        assert state.name == "Device 1"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.2"
        assert state.attributes["mac"] == "CC:50:E3:96:29:78"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert state.attributes["signal"] is None
        assert state.attributes["down_speed"] == "9.54 MB/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        device = device_registry.async_get_device(
            set(), {(dr.CONNECTION_NETWORK_MAC, "CC:50:E3:96:29:78")}
        )

        assert device.manufacturer == MANUFACTURERS["CC50E3"]


async def test_init_detect_url(hass: HomeAssistant) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)
        mock_socket.return_value.connect_ex = Mock(return_value=0)

        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.device_list = AsyncMock(
            return_value=json.loads(
                load_fixture("device_list_detect_manufacturer_data.json")
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        device_registry = dr.async_get(hass)

        state: State = hass.states.get(_generate_id("CC:50:E3:96:29:78"))
        assert state.state == STATE_HOME
        assert state.name == "Device 1"
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["source_type"] == SOURCE_TYPE_ROUTER
        assert state.attributes["ip"] == "192.168.31.2"
        assert state.attributes["mac"] == "CC:50:E3:96:29:78"
        assert state.attributes["scanner"] == DOMAIN
        assert state.attributes["online"] == "8:05:01"
        assert state.attributes["connection"] == Connection.WIFI_2_4.phrase  # type: ignore
        assert state.attributes["router_mac"] == "00:00:00:00:00:00"
        assert state.attributes["signal"] is None
        assert state.attributes["down_speed"] == "9.54 MB/s"
        assert state.attributes["up_speed"] == "0 B/s"
        assert state.attributes["attribution"] == ATTRIBUTION

        device = device_registry.async_get_device(
            set(), {(dr.CONNECTION_NETWORK_MAC, "CC:50:E3:96:29:78")}
        )

        assert device.configuration_url == "http://192.168.31.2"


def _generate_id(mac: str) -> str:
    """Generate unique id

    :param mac: str
    :return str
    """

    return generate_entity_id(DEVICE_TRACKER_ENTITY_ID_FORMAT, mac)
