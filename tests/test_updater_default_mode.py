"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import json
import logging
from typing import Final
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from httpx import codes
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from custom_components.miwifi.const import (
    ATTR_BINARY_SENSOR_DUAL_BAND,
    ATTR_BINARY_SENSOR_WAN_STATE,
    ATTR_DEVICE_HW_VERSION,
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_DEVICE_MANUFACTURER,
    ATTR_DEVICE_MODEL,
    ATTR_DEVICE_NAME,
    ATTR_DEVICE_SW_VERSION,
    ATTR_LIGHT_LED,
    ATTR_MODEL,
    ATTR_SELECT_WIFI_2_4_CHANNEL,
    ATTR_SELECT_WIFI_2_4_CHANNELS,
    ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH,
    ATTR_SELECT_WIFI_5_0_CHANNEL,
    ATTR_SELECT_WIFI_5_0_CHANNELS,
    ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH,
    ATTR_SENSOR_DEVICES,
    ATTR_SENSOR_DEVICES_2_4,
    ATTR_SENSOR_DEVICES_5_0,
    ATTR_SENSOR_DEVICES_5_0_GAME,
    ATTR_SENSOR_DEVICES_GUEST,
    ATTR_SENSOR_DEVICES_LAN,
    ATTR_SENSOR_MEMORY_TOTAL,
    ATTR_SENSOR_MEMORY_USAGE,
    ATTR_SENSOR_MODE,
    ATTR_SENSOR_TEMPERATURE,
    ATTR_SENSOR_UPTIME,
    ATTR_SENSOR_WAN_DOWNLOAD_SPEED,
    ATTR_SENSOR_WAN_UPLOAD_SPEED,
    ATTR_STATE,
    ATTR_SWITCH_WIFI_2_4,
    ATTR_SWITCH_WIFI_5_0,
    ATTR_SWITCH_WIFI_GUEST,
    ATTR_TRACKER_CONNECTION,
    ATTR_TRACKER_DOWN_SPEED,
    ATTR_TRACKER_ENTRY_ID,
    ATTR_TRACKER_IP,
    ATTR_TRACKER_LAST_ACTIVITY,
    ATTR_TRACKER_MAC,
    ATTR_TRACKER_NAME,
    ATTR_TRACKER_ONLINE,
    ATTR_TRACKER_OPTIONAL_MAC,
    ATTR_TRACKER_ROUTER_MAC_ADDRESS,
    ATTR_TRACKER_SIGNAL,
    ATTR_TRACKER_UP_SPEED,
    ATTR_TRACKER_UPDATER_ENTRY_ID,
    ATTR_UPDATE_CURRENT_VERSION,
    ATTR_UPDATE_FIRMWARE,
    ATTR_UPDATE_LATEST_VERSION,
    ATTR_UPDATE_TITLE,
    ATTR_WIFI_2_4_DATA,
    ATTR_WIFI_5_0_DATA,
    ATTR_WIFI_ADAPTER_LENGTH,
    ATTR_WIFI_GUEST_DATA,
    DEFAULT_MANUFACTURER,
    DOMAIN,
)
from custom_components.miwifi.enum import Connection, Mode, Model
from custom_components.miwifi.updater import LuciUpdater
from tests.setup import async_mock_luci_client, async_setup

MOCK_IP_ADDRESS: Final = "192.168.31.1"
MOCK_PASSWORD: Final = "**REDACTED**"

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_updater_default_mode(
    hass: HomeAssistant,
) -> None:
    """Test updater.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_dispatcher_send"
    ) as mock_async_dispatcher_send, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]
        config_entry: MockConfigEntry = setup_data[1]

        await updater.async_config_entry_first_refresh()
        await updater.async_stop()

        await hass.async_block_till_done()

    assert updater.last_update_success
    assert updater.new_device_callback is not None
    assert len(updater.data) > 0
    assert len(updater.devices) == 3
    assert len(updater._signals) == 2
    assert len(updater._moved_devices) == 0
    assert updater.code == codes.OK
    assert not updater.is_repeater

    assert updater.device_info["identifiers"] == {(DOMAIN, "00:00:00:00:00:00")}
    assert updater.device_info["connections"] == {
        (CONF_IP_ADDRESS, "192.168.31.1"),
        (CONNECTION_NETWORK_MAC, "00:00:00:00:00:00"),
    }
    assert updater.device_info["name"] == "XIAOMI RA67"
    assert updater.device_info["manufacturer"] == "Xiaomi"
    assert updater.device_info["model"] == "xiaomi.router.ra67"
    assert updater.device_info["sw_version"] == "3.0.34 (CN)"
    assert updater.device_info["hw_version"] == "29543/F0SW88385"
    assert updater.device_info["configuration_url"] == f"http://{MOCK_IP_ADDRESS}/"

    assert updater.data[ATTR_DEVICE_MODEL] == "xiaomi.router.ra67"
    assert updater.data[ATTR_DEVICE_MANUFACTURER] == DEFAULT_MANUFACTURER
    assert updater.data[ATTR_DEVICE_NAME] == "XIAOMI RA67"
    assert updater.data[ATTR_DEVICE_SW_VERSION] == "3.0.34 (CN)"
    assert updater.data[ATTR_DEVICE_HW_VERSION] == "29543/F0SW88385"
    assert updater.data[ATTR_MODEL] == Model.RA67
    assert updater.data[ATTR_DEVICE_MAC_ADDRESS] == "00:00:00:00:00:00"
    assert updater.data[ATTR_UPDATE_CURRENT_VERSION] == "3.0.34"
    assert updater.data[ATTR_SENSOR_UPTIME] == "8:06:26"
    assert updater.data[ATTR_SENSOR_MEMORY_USAGE] == 53
    assert updater.data[ATTR_SENSOR_MEMORY_TOTAL] == 256
    assert updater.data[ATTR_SENSOR_TEMPERATURE] == 0.0
    assert updater.data[ATTR_SENSOR_WAN_DOWNLOAD_SPEED] == 225064.0
    assert updater.data[ATTR_SENSOR_WAN_UPLOAD_SPEED] == 19276.0
    assert updater.data[ATTR_UPDATE_FIRMWARE][ATTR_UPDATE_CURRENT_VERSION] == "3.0.34"
    assert updater.data[ATTR_UPDATE_FIRMWARE][ATTR_UPDATE_LATEST_VERSION] == "3.0.34"
    assert (
        updater.data[ATTR_UPDATE_FIRMWARE][ATTR_UPDATE_TITLE]
        == "Xiaomi RA67 (XIAOMI RA67)"
    )
    assert updater.data[ATTR_SENSOR_MODE] == Mode.DEFAULT
    assert updater.data[ATTR_BINARY_SENSOR_WAN_STATE]
    assert updater.data[ATTR_LIGHT_LED]
    assert not updater.data[ATTR_BINARY_SENSOR_DUAL_BAND]
    assert updater.data[ATTR_SWITCH_WIFI_2_4]
    assert updater.data[ATTR_SELECT_WIFI_2_4_CHANNEL] == "2"
    assert updater.data[ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH] == "max"
    assert updater.data[ATTR_WIFI_2_4_DATA] == {
        "ssid": "**REDACTED**",
        "pwd": "**REDACTED**",
        "bandwidth": "20",
        "channel": 2,
        "encryption": "psk2",
        "txpwr": "max",
        "hidden": "0",
        "on": "1",
        "txbf": "3",
    }
    assert updater.data[ATTR_SWITCH_WIFI_5_0]
    assert updater.data[ATTR_SELECT_WIFI_5_0_CHANNEL] == "149"
    assert updater.data[ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH] == "max"
    assert updater.data[ATTR_WIFI_5_0_DATA] == {
        "ssid": "**REDACTED**",
        "pwd": "**REDACTED**",
        "bandwidth": "0",
        "channel": 149,
        "encryption": "psk2",
        "txpwr": "max",
        "hidden": "0",
        "on": "1",
        "txbf": "3",
    }
    assert not updater.data[ATTR_SWITCH_WIFI_GUEST]
    assert updater.data[ATTR_WIFI_GUEST_DATA] == {
        "ssid": "**REDACTED**",
        "pwd": "**REDACTED**",
        "encryption": "none",
        "on": 0,
    }
    assert updater.data[ATTR_WIFI_ADAPTER_LENGTH] == 2
    assert updater.data[ATTR_SELECT_WIFI_2_4_CHANNELS] == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
        "13",
    ]
    assert updater.data[ATTR_SELECT_WIFI_5_0_CHANNELS] == [
        "36",
        "40",
        "44",
        "48",
        "149",
        "153",
        "157",
        "161",
    ]
    assert updater.data[ATTR_SENSOR_DEVICES] == 3
    assert updater.data[ATTR_SENSOR_DEVICES_LAN] == 1
    assert updater.data[ATTR_SENSOR_DEVICES_GUEST] == 0
    assert updater.data[ATTR_SENSOR_DEVICES_2_4] == 1
    assert updater.data[ATTR_SENSOR_DEVICES_5_0] == 1
    assert updater.data[ATTR_SENSOR_DEVICES_5_0_GAME] == 0
    assert updater.data[ATTR_STATE]

    assert updater._signals == {
        "00:00:00:00:00:01": 100,
        "00:00:00:00:00:02": 100,
    }
    assert updater.devices == {
        "00:00:00:00:00:01": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:01",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: 100,
            ATTR_TRACKER_NAME: "Device 1",
            ATTR_TRACKER_IP: "192.168.31.2",
            ATTR_TRACKER_CONNECTION: Connection.WIFI_2_4,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:01"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:02": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:02",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: 100,
            ATTR_TRACKER_NAME: "Device 2",
            ATTR_TRACKER_IP: "192.168.31.3",
            ATTR_TRACKER_CONNECTION: Connection.WIFI_5_0,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:02"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:03": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:03",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: None,
            ATTR_TRACKER_NAME: "Device 3",
            ATTR_TRACKER_IP: "192.168.31.4",
            ATTR_TRACKER_CONNECTION: Connection.LAN,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:03"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
    }

    assert len(mock_async_dispatcher_send.mock_calls) == 3
    assert len(mock_luci_client.mock_calls) == 16


async def test_updater_restore_data(hass: HomeAssistant) -> None:
    """Test updater.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_dispatcher_send"
    ) as mock_async_dispatcher_send, patch(
        "custom_components.miwifi.helper.Store"
    ) as mock_store, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_store.return_value.async_load = AsyncMock(
            return_value=json.loads(load_fixture("store_data.json"))
        )
        mock_store.return_value.async_save = AsyncMock(return_value=None)

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]
        config_entry: MockConfigEntry = setup_data[1]

        await updater.async_config_entry_first_refresh()
        await updater.async_stop()

        await hass.async_block_till_done()

    assert updater.data[ATTR_SENSOR_DEVICES] == 3
    assert updater.data[ATTR_SENSOR_DEVICES_LAN] == 1
    assert updater.data[ATTR_SENSOR_DEVICES_GUEST] == 0
    assert updater.data[ATTR_SENSOR_DEVICES_2_4] == 1
    assert updater.data[ATTR_SENSOR_DEVICES_5_0] == 1
    assert updater.data[ATTR_SENSOR_DEVICES_5_0_GAME] == 0
    assert updater.data[ATTR_STATE]

    assert updater.devices == {
        "00:00:00:00:00:01": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:01",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: 100,
            ATTR_TRACKER_NAME: "Device 1",
            ATTR_TRACKER_IP: "192.168.31.2",
            ATTR_TRACKER_CONNECTION: Connection.WIFI_2_4,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:01"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:02": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:02",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: 100,
            ATTR_TRACKER_NAME: "Device 2",
            ATTR_TRACKER_IP: "192.168.31.3",
            ATTR_TRACKER_CONNECTION: Connection.WIFI_5_0,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:02"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:03": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:03",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: None,
            ATTR_TRACKER_NAME: "Device 3",
            ATTR_TRACKER_IP: "192.168.31.4",
            ATTR_TRACKER_CONNECTION: Connection.LAN,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:03"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:05": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:05",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: None,
            ATTR_TRACKER_NAME: "Device 5",
            ATTR_TRACKER_IP: "192.168.31.55",
            ATTR_TRACKER_CONNECTION: Connection.LAN,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: "2022-04-25T22:33:39",
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
    }

    assert len(mock_async_dispatcher_send.mock_calls) == 4
    assert len(mock_store.mock_calls) == 3
    assert len(mock_luci_client.mock_calls) == 16


async def test_updater_incorrect_connection_restore_data(hass: HomeAssistant) -> None:
    """Test updater.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_dispatcher_send"
    ) as mock_async_dispatcher_send, patch(
        "custom_components.miwifi.helper.Store"
    ) as mock_store, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_store.return_value.async_load = AsyncMock(
            return_value=json.loads(
                load_fixture("store_incorrect_connection_data.json")
            )
        )
        mock_store.return_value.async_save = AsyncMock(return_value=None)

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]
        config_entry: MockConfigEntry = setup_data[1]

        await updater.async_config_entry_first_refresh()
        await updater.async_stop()

        await hass.async_block_till_done()

    assert updater.data[ATTR_SENSOR_DEVICES] == 3
    assert updater.data[ATTR_SENSOR_DEVICES_LAN] == 1
    assert updater.data[ATTR_SENSOR_DEVICES_GUEST] == 0
    assert updater.data[ATTR_SENSOR_DEVICES_2_4] == 1
    assert updater.data[ATTR_SENSOR_DEVICES_5_0] == 1
    assert updater.data[ATTR_SENSOR_DEVICES_5_0_GAME] == 0
    assert updater.data[ATTR_STATE]

    assert updater.devices == {
        "00:00:00:00:00:01": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:01",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: 100,
            ATTR_TRACKER_NAME: "Device 1",
            ATTR_TRACKER_IP: "192.168.31.2",
            ATTR_TRACKER_CONNECTION: Connection.WIFI_2_4,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:01"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:02": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:02",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: 100,
            ATTR_TRACKER_NAME: "Device 2",
            ATTR_TRACKER_IP: "192.168.31.3",
            ATTR_TRACKER_CONNECTION: Connection.WIFI_5_0,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:02"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:03": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:03",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: None,
            ATTR_TRACKER_NAME: "Device 3",
            ATTR_TRACKER_IP: "192.168.31.4",
            ATTR_TRACKER_CONNECTION: Connection.LAN,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:03"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:05": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:05",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: None,
            ATTR_TRACKER_NAME: "Device 5",
            ATTR_TRACKER_IP: "192.168.31.55",
            ATTR_TRACKER_CONNECTION: None,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: "2022-04-25T22:33:39",
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
    }

    assert len(mock_async_dispatcher_send.mock_calls) == 4
    assert len(mock_store.mock_calls) == 3
    assert len(mock_luci_client.mock_calls) == 16


async def test_updater_incorrect_mac_default_mode(hass: HomeAssistant) -> None:
    """Test updater.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_dispatcher_send"
    ) as mock_async_dispatcher_send, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.device_list = AsyncMock(
            return_value=json.loads(load_fixture("device_list_incorrect_mac_data.json"))
        )

        setup_data: list = await async_setup(hass)

        updater: LuciUpdater = setup_data[0]
        config_entry: MockConfigEntry = setup_data[1]

        await updater.async_config_entry_first_refresh()
        await updater.async_stop()

        await hass.async_block_till_done()

    assert updater.last_update_success
    assert updater.new_device_callback is not None
    assert len(updater.data) > 0
    assert len(updater.devices) == 2
    assert len(updater._signals) == 2
    assert len(updater._moved_devices) == 0
    assert updater.code == codes.OK
    assert not updater.is_repeater

    assert updater.data[ATTR_SENSOR_DEVICES] == 2
    assert updater.data[ATTR_SENSOR_DEVICES_LAN] == 1
    assert updater.data[ATTR_SENSOR_DEVICES_GUEST] == 0
    assert updater.data[ATTR_SENSOR_DEVICES_2_4] == 0
    assert updater.data[ATTR_SENSOR_DEVICES_5_0] == 1
    assert updater.data[ATTR_SENSOR_DEVICES_5_0_GAME] == 0
    assert updater.data[ATTR_STATE]

    assert updater._signals == {
        "00:00:00:00:00:01": 100,
        "00:00:00:00:00:02": 100,
    }
    assert updater.devices == {
        "00:00:00:00:00:02": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:02",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: 100,
            ATTR_TRACKER_NAME: "Device 2",
            ATTR_TRACKER_IP: "192.168.31.3",
            ATTR_TRACKER_CONNECTION: Connection.WIFI_5_0,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:02"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:03": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:03",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: None,
            ATTR_TRACKER_NAME: "Device 3",
            ATTR_TRACKER_IP: "192.168.31.4",
            ATTR_TRACKER_CONNECTION: Connection.LAN,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:03"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
    }

    assert len(mock_async_dispatcher_send.mock_calls) == 2
    assert len(mock_luci_client.mock_calls) == 16


async def test_updater_default_mode_auto_remove(hass: HomeAssistant) -> None:
    """Test updater.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_dispatcher_send"
    ), patch(
        "custom_components.miwifi.helper.Store"
    ) as mock_store, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_store.return_value.async_load = AsyncMock(
            return_value=json.loads(load_fixture("store_data.json"))
        )
        mock_store.return_value.async_save = AsyncMock(return_value=None)

        setup_data: list = await async_setup(hass, activity_days=1)

        updater: LuciUpdater = setup_data[0]
        config_entry: MockConfigEntry = setup_data[1]

        await updater.async_config_entry_first_refresh()
        await updater.async_stop()

        await hass.async_block_till_done()

    assert len(updater.devices) == 3

    assert updater.devices == {
        "00:00:00:00:00:01": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:01",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: 100,
            ATTR_TRACKER_NAME: "Device 1",
            ATTR_TRACKER_IP: "192.168.31.2",
            ATTR_TRACKER_CONNECTION: Connection.WIFI_2_4,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:01"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:02": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:02",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: 100,
            ATTR_TRACKER_NAME: "Device 2",
            ATTR_TRACKER_IP: "192.168.31.3",
            ATTR_TRACKER_CONNECTION: Connection.WIFI_5_0,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:02"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:03": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:03",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: None,
            ATTR_TRACKER_NAME: "Device 3",
            ATTR_TRACKER_IP: "192.168.31.4",
            ATTR_TRACKER_CONNECTION: Connection.LAN,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:03"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
    }


async def test_updater_default_mode_auto_remove_incorrect(hass: HomeAssistant) -> None:
    """Test updater.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_dispatcher_send"
    ), patch(
        "custom_components.miwifi.helper.Store"
    ) as mock_store, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_store.return_value.async_load = AsyncMock(
            return_value=json.loads(
                load_fixture("store_incorrect_last_activity_data.json")
            )
        )
        mock_store.return_value.async_save = AsyncMock(return_value=None)

        setup_data: list = await async_setup(hass, activity_days=1)

        updater: LuciUpdater = setup_data[0]
        config_entry: MockConfigEntry = setup_data[1]

        await updater.async_config_entry_first_refresh()
        await updater.async_stop()

        await hass.async_block_till_done()

    assert len(updater.devices) == 4

    assert updater.devices == {
        "00:00:00:00:00:01": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:01",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: 100,
            ATTR_TRACKER_NAME: "Device 1",
            ATTR_TRACKER_IP: "192.168.31.2",
            ATTR_TRACKER_CONNECTION: Connection.WIFI_2_4,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:01"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:02": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:02",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: 100,
            ATTR_TRACKER_NAME: "Device 2",
            ATTR_TRACKER_IP: "192.168.31.3",
            ATTR_TRACKER_CONNECTION: Connection.WIFI_5_0,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:02"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:03": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:03",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: None,
            ATTR_TRACKER_NAME: "Device 3",
            ATTR_TRACKER_IP: "192.168.31.4",
            ATTR_TRACKER_CONNECTION: Connection.LAN,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:03"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
        "00:00:00:00:00:05": {
            ATTR_TRACKER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_UPDATER_ENTRY_ID: config_entry.entry_id,
            ATTR_TRACKER_MAC: "00:00:00:00:00:05",
            ATTR_TRACKER_ROUTER_MAC_ADDRESS: "00:00:00:00:00:00",
            ATTR_TRACKER_SIGNAL: None,
            ATTR_TRACKER_NAME: "Device 5",
            ATTR_TRACKER_IP: "192.168.31.55",
            ATTR_TRACKER_CONNECTION: Connection.LAN,
            ATTR_TRACKER_DOWN_SPEED: 0.0,
            ATTR_TRACKER_UP_SPEED: 0.0,
            ATTR_TRACKER_ONLINE: "8:05:01",
            ATTR_TRACKER_LAST_ACTIVITY: updater.devices["00:00:00:00:00:03"][
                "last_activity"
            ],
            ATTR_TRACKER_OPTIONAL_MAC: None,
        },
    }
