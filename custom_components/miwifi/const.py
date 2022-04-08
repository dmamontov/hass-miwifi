"""General constants."""
from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

# fmt: off
DOMAIN: Final = "miwifi"
ATTRIBUTION: Final = "Data provided by MiWifi"

PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.LIGHT,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.DEVICE_TRACKER,
    Platform.CAMERA,
]

"""Discovery const"""
DISCOVERY: Final = "discovery"
DISCOVERY_INTERVAL: Final = timedelta(minutes=60)

"""Helper const"""
UPDATER: Final = "updater"
UPDATE_LISTENER: Final = "update_listener"
RELOAD_ENTRY: Final = "reload_entry"
OPTION_IS_FROM_FLOW: Final = "is_from_flow"
STORAGE_VERSION: Final = 1
SIGNAL_NEW_DEVICE: Final = f"{DOMAIN}-device-new"

"""Custom conf"""
CONF_IS_FORCE_LOAD: Final = "is_force_load"
CONF_ACTIVITY_DAYS: Final = "activity_days"

"""Default settings"""
DEFAULT_RETRY: Final = 10
DEFAULT_SCAN_INTERVAL: Final = 30
DEFAULT_TIMEOUT: Final = 20
DEFAULT_ACTIVITY_DAYS: Final = 30
DEFAULT_CALL_DELAY: Final = 1
DEFAULT_SLEEP: Final = 3
DEFAULT_NAME: Final = "MiWifi router"
DEFAULT_MANUFACTURER: Final = "Xiaomi"

"""Luci API client const"""
CLIENT_ADDRESS: Final = "miwifi.com"
CLIENT_ADDRESS_IP: Final = "192.168.31.1"
CLIENT_URL: Final = "http://{ip}/cgi-bin/luci"
CLIENT_USERNAME: Final = "admin"
CLIENT_LOGIN_TYPE: Final = 2
CLIENT_NONCE_TYPE: Final = 0
CLIENT_PUBLIC_KEY: Final = "a2ffa5c9be07488bbb04a3a47d3c5f6a"

"""Attributes"""
ATTR_STATE: Final = "state"
ATTR_STATE_NAME: Final = "State"

ATTR_MODEL: Final = "model"

ATTR_DEVICE_MODEL: Final = "device_model"
ATTR_DEVICE_MAC_ADDRESS: Final = "device_mac_address"
ATTR_DEVICE_NAME: Final = "device_name"
ATTR_DEVICE_MANUFACTURER: Final = "device_manufacturer"
ATTR_DEVICE_SW_VERSION: Final = "device_sw_version"

ATTR_WIFI_NAME: Final = "Wifi"
ATTR_WIFI_DATA_FIELDS: Final = {
    "ssid": "ssid",
    "password": "pwd",
    "encryption": "encryption",
    "channelInfo.channel": "channel",
    "channelInfo.bandwidth": "bandwidth",
    "txpwr": "txpwr",
    "hidden": "hidden",
    "status": "on",
    "txbf": "txbf",
    "weakenable": "weakenable",
    "weakthreshold": "weakthreshold",
    "kickthreshold": "kickthreshold",
}
ATTR_WIFI_2_4_DATA: Final = "wifi_2_4_data"
ATTR_WIFI_5_0_DATA: Final = "wifi_5_0_data"
ATTR_WIFI_5_0_GAME: Final = "wifi_5_0_game_data"

ATTR_WIFI_ADAPTER_LENGTH: Final = "wifi_adapter_length"

"""Sensor attributes"""
ATTR_SENSOR_UPTIME: Final = "uptime"
ATTR_SENSOR_UPTIME_NAME: Final = "Uptime"

ATTR_SENSOR_MEMORY_USAGE: Final = "memory_usage"
ATTR_SENSOR_MEMORY_USAGE_NAME: Final = "Memory usage"

ATTR_SENSOR_MEMORY_TOTAL: Final = "memory_total"
ATTR_SENSOR_MEMORY_TOTAL_NAME: Final = "Memory total"

ATTR_SENSOR_TEMPERATURE: Final = "temperature"
ATTR_SENSOR_TEMPERATURE_NAME: Final = "Temperature"

ATTR_SENSOR_MODE: Final = "mode"
ATTR_SENSOR_MODE_NAME: Final = "Mode"

ATTR_SENSOR_DEVICES: Final = "devices"
ATTR_SENSOR_DEVICES_NAME: Final = "Devices"

ATTR_SENSOR_DEVICES_LAN: Final = f"{ATTR_SENSOR_DEVICES}_lan"
ATTR_SENSOR_DEVICES_LAN_NAME: Final = f"{ATTR_SENSOR_DEVICES_NAME} lan"

ATTR_SENSOR_DEVICES_GUEST: Final = f"{ATTR_SENSOR_DEVICES}_guest"
ATTR_SENSOR_DEVICES_GUEST_NAME: Final = f"{ATTR_SENSOR_DEVICES_NAME} guest"

ATTR_SENSOR_DEVICES_2_4: Final = f"{ATTR_SENSOR_DEVICES}_2_4"
ATTR_SENSOR_DEVICES_2_4_NAME: Final = f"{ATTR_SENSOR_DEVICES_NAME} 2.4G"

ATTR_SENSOR_DEVICES_5_0: Final = f"{ATTR_SENSOR_DEVICES}_5_0"
ATTR_SENSOR_DEVICES_5_0_NAME: Final = f"{ATTR_SENSOR_DEVICES_NAME} 5G"

ATTR_SENSOR_DEVICES_5_0_GAME: Final = f"{ATTR_SENSOR_DEVICES}_5_0_game"
ATTR_SENSOR_DEVICES_5_0_GAME_NAME: Final = f"{ATTR_SENSOR_DEVICES_NAME} 5G game"

"""Binary sensor attributes"""
ATTR_BINARY_SENSOR_WAN_STATE: Final = "wan_state"
ATTR_BINARY_SENSOR_WAN_STATE_NAME: Final = "Wan state"

ATTR_BINARY_SENSOR_DUAL_BAND: Final = "dual_band"
ATTR_BINARY_SENSOR_DUAL_BAND_NAME: Final = "Dual band"

"""Light attributes"""
ATTR_LIGHT_LED: Final = "led"
ATTR_LIGHT_LED_NAME: Final = "Led"

"""Button attributes"""
ATTR_BUTTON_REBOOT: Final = "reboot"
ATTR_BUTTON_REBOOT_NAME: Final = "Reboot"

"""Switch attributes"""
ATTR_SWITCH_WIFI_2_4: Final = "wifi_2_4"
ATTR_SWITCH_WIFI_2_4_NAME: Final = f"{ATTR_WIFI_NAME} 2.4G"

ATTR_SWITCH_WIFI_5_0: Final = "wifi_5_0"
ATTR_SWITCH_WIFI_5_0_NAME: Final = f"{ATTR_WIFI_NAME} 5G"

ATTR_SWITCH_WIFI_5_0_GAME: Final = "wifi_5_0_game"
ATTR_SWITCH_WIFI_5_0_GAME_NAME: Final = f"{ATTR_WIFI_NAME} 5G game"

"""Select attributes"""
ATTR_SELECT_WIFI_2_4_CHANNEL: Final = "wifi_2_4_channel"
ATTR_SELECT_WIFI_2_4_CHANNELS: Final = "wifi_2_4_channels"
ATTR_SELECT_WIFI_2_4_CHANNEL_NAME: Final = f"{ATTR_WIFI_NAME} 2.4G channel"

ATTR_SELECT_WIFI_5_0_CHANNEL: Final = "wifi_5_0_channel"
ATTR_SELECT_WIFI_5_0_CHANNELS: Final = "wifi_5_0_channels"
ATTR_SELECT_WIFI_5_0_CHANNEL_NAME: Final = f"{ATTR_WIFI_NAME} 5G channel"

ATTR_SELECT_WIFI_5_0_GAME_CHANNEL: Final = "wifi_5_0_game_channel"
ATTR_SELECT_WIFI_5_0_GAME_CHANNELS: Final = "wifi_5_0_game_channels"
ATTR_SELECT_WIFI_5_0_GAME_CHANNEL_NAME: Final = f"{ATTR_WIFI_NAME} 5G game channel"

ATTR_SELECT_SIGNAL_STRENGTH_OPTIONS: Final = ["min", "mid", "max"]

ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH: Final = "wifi_2_4_signal_strength"
ATTR_SELECT_WIFI_2_4_SIGNAL_STRENGTH_NAME: Final = f"{ATTR_WIFI_NAME} 2.4G signal strength"

ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH: Final = "wifi_5_0_signal_strength"
ATTR_SELECT_WIFI_5_0_SIGNAL_STRENGTH_NAME: Final = f"{ATTR_WIFI_NAME} 5G signal strength"

ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH: Final = "wifi_5_0_game_signal_strength"
ATTR_SELECT_WIFI_5_0_GAME_SIGNAL_STRENGTH_NAME: Final = f"{ATTR_WIFI_NAME} 5G game signal strength"

"""Camera attributes"""
ATTR_CAMERA_IMAGE: Final = "image"
ATTR_CAMERA_IMAGE_NAME: Final = "Image"

"""Device tracker attributes"""
ATTR_TRACKER_ENTRY_ID: Final = "entry_id"
ATTR_TRACKER_UPDATER_ENTRY_ID: Final = "updater_entry_id"
ATTR_TRACKER_SCANNER: Final = "scanner"
ATTR_TRACKER_MAC: Final = "mac"
ATTR_TRACKER_ROUTER_MAC_ADDRESS: Final = "router_mac"
ATTR_TRACKER_SIGNAL: Final = "signal"
ATTR_TRACKER_NAME: Final = "name"
ATTR_TRACKER_CONNECTION: Final = "connection"
ATTR_TRACKER_IP: Final = "ip"
ATTR_TRACKER_ONLINE: Final = "online"
ATTR_TRACKER_DOWN_SPEED: Final = "down_speed"
ATTR_TRACKER_UP_SPEED: Final = "up_speed"
ATTR_TRACKER_LAST_ACTIVITY: Final = "last_activity"
# fmt: on
