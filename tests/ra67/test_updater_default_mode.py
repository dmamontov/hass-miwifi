"""Tests for the miwifi component."""

from __future__ import annotations

from typing import Final
import logging
from unittest.mock import patch
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from httpx import codes

from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from custom_components.miwifi.const import DOMAIN
from custom_components.miwifi.enum import Model, Mode, Connection
from custom_components.miwifi.updater import LuciUpdater

from tests.setup import async_mock_luci_client, async_setup

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

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_dispatcher_send"
    ) as mock_async_dispatcher_send:
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
    assert len(updater._manufacturers) > 0
    assert len(updater._signals) == 2
    assert len(updater._moved_devices) == 0
    assert updater.code == codes.OK
    assert not updater.is_repeater

    assert updater.device_info["identifiers"] == {(DOMAIN, "00:00:00:00:00:00")}
    assert updater.device_info["connections"] == {
        (CONNECTION_NETWORK_MAC, "00:00:00:00:00:00")
    }
    assert updater.device_info["name"] == "XIAOMI RA67"
    assert updater.device_info["manufacturer"] == "Xiaomi"
    assert updater.device_info["model"] == "xiaomi.router.ra67"
    assert updater.device_info["sw_version"] == "3.0.34 (CN)"
    assert updater.device_info["configuration_url"] == f"http://{MOCK_IP_ADDRESS}/"

    assert updater.data["device_model"] == "xiaomi.router.ra67"
    assert updater.data["device_manufacturer"] == "Xiaomi"
    assert updater.data["device_name"] == "XIAOMI RA67"
    assert updater.data["device_sw_version"] == "3.0.34 (CN)"
    assert updater.data["model"] == Model.RA67
    assert updater.data["image"] == load_fixture("image_data.txt")
    assert updater.data["device_mac_address"] == "00:00:00:00:00:00"
    assert updater.data["current_version"] == "3.0.34"
    assert updater.data["uptime"] == "8:06:26"
    assert updater.data["memory_usage"] == 53
    assert updater.data["memory_total"] == 256
    assert updater.data["temperature"] == 0.0
    assert updater.data["wan_download_speed"] == 225064.0
    assert updater.data["wan_upload_speed"] == 19276.0
    assert updater.data["firmware"]["current_version"] == "3.0.34"
    assert updater.data["firmware"]["latest_version"] == "3.0.34"
    assert updater.data["firmware"]["title"] == "Xiaomi RA67 (XIAOMI RA67)"
    assert updater.data["mode"] == Mode.DEFAULT
    assert updater.data["wan_state"]
    assert updater.data["led"]
    assert not updater.data["dual_band"]
    assert updater.data["wifi_2_4"]
    assert updater.data["wifi_2_4_channel"] == "2"
    assert updater.data["wifi_2_4_signal_strength"] == "max"
    assert updater.data["wifi_2_4_data"] == {
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
    assert updater.data["wifi_5_0"]
    assert updater.data["wifi_5_0_channel"] == "149"
    assert updater.data["wifi_2_4_signal_strength"] == "max"
    assert updater.data["wifi_5_0_data"] == {
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
    assert updater.data["wifi_adapter_length"] == 2
    assert updater.data["wifi_2_4_channels"] == [
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
    assert updater.data["wifi_5_0_channels"] == [
        "36",
        "40",
        "44",
        "48",
        "149",
        "153",
        "157",
        "161",
    ]
    assert updater.data["devices"] == 3
    assert updater.data["devices_lan"] == 1
    assert updater.data["devices_guest"] == 0
    assert updater.data["devices_2_4"] == 1
    assert updater.data["devices_5_0"] == 1
    assert updater.data["devices_5_0_game"] == 0
    assert updater.data["state"]

    assert updater._signals == {"00:00:00:00:00:01": 100, "00:00:00:00:00:02": 100}
    assert updater.devices == {
        "00:00:00:00:00:01": {
            "entry_id": config_entry.entry_id,
            "updater_entry_id": config_entry.entry_id,
            "mac": "00:00:00:00:00:01",
            "router_mac": "00:00:00:00:00:00",
            "signal": 100,
            "name": "Device 1",
            "ip": "192.168.31.2",
            "connection": Connection.WIFI_2_4,
            "down_speed": 0.0,
            "up_speed": 0.0,
            "online": "8:05:01",
            "last_activity": updater.devices["00:00:00:00:00:01"]["last_activity"],
            "optional_mac": None,
        },
        "00:00:00:00:00:02": {
            "entry_id": config_entry.entry_id,
            "updater_entry_id": config_entry.entry_id,
            "mac": "00:00:00:00:00:02",
            "router_mac": "00:00:00:00:00:00",
            "signal": 100,
            "name": "Device 2",
            "ip": "192.168.31.3",
            "connection": Connection.WIFI_5_0,
            "down_speed": 0.0,
            "up_speed": 0.0,
            "online": "8:05:01",
            "last_activity": updater.devices["00:00:00:00:00:02"]["last_activity"],
            "optional_mac": None,
        },
        "00:00:00:00:00:03": {
            "entry_id": config_entry.entry_id,
            "updater_entry_id": config_entry.entry_id,
            "mac": "00:00:00:00:00:03",
            "router_mac": "00:00:00:00:00:00",
            "signal": None,
            "name": "Device 3",
            "ip": "192.168.31.4",
            "connection": Connection.LAN,
            "down_speed": 0.0,
            "up_speed": 0.0,
            "online": "8:05:01",
            "last_activity": updater.devices["00:00:00:00:00:03"]["last_activity"],
            "optional_mac": None,
        },
    }

    assert len(mock_async_dispatcher_send.mock_calls) == 3
    assert len(mock_luci_client.mock_calls) == 16
