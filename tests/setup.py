"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import json
import logging
import urllib.parse
from typing import Final
from unittest.mock import AsyncMock

from homeassistant import setup
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from custom_components.miwifi.const import (
    CONF_ACTIVITY_DAYS,
    CONF_IS_FORCE_LOAD,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    OPTION_IS_FROM_FLOW,
    SIGNAL_NEW_DEVICE,
    UPDATER,
)
from custom_components.miwifi.helper import get_config_value, get_store
from custom_components.miwifi.updater import LuciUpdater

MOCK_IP_ADDRESS: Final = "192.168.31.1"
MOCK_PASSWORD: Final = "**REDACTED**"
OPTIONS_FLOW_DATA: Final = {
    CONF_IP_ADDRESS: MOCK_IP_ADDRESS,
    CONF_PASSWORD: MOCK_PASSWORD,
    CONF_TIMEOUT: DEFAULT_TIMEOUT,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
}

_LOGGER = logging.getLogger(__name__)


async def async_setup(
    hass: HomeAssistant,
    _ip: str = MOCK_IP_ADDRESS,
    without_store: bool = False,
    activity_days: int = 0,
    is_force: bool = False,
) -> list:
    """Setup.

    :param hass: HomeAssistant
    :param _ip: str
    :param without_store: bool
    :param activity_days: int
    :param is_force: bool
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=OPTIONS_FLOW_DATA
        | {
            CONF_IP_ADDRESS: _ip,
            CONF_IS_FORCE_LOAD: is_force,
            CONF_ACTIVITY_DAYS: activity_days,
        },
        options={OPTION_IS_FROM_FLOW: True},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    updater: LuciUpdater = LuciUpdater(
        hass,
        _ip,
        get_config_value(config_entry, CONF_PASSWORD),
        get_config_value(config_entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        get_config_value(config_entry, CONF_TIMEOUT, DEFAULT_TIMEOUT),
        get_config_value(config_entry, CONF_IS_FORCE_LOAD, is_force),
        activity_days,
        get_store(hass, _ip) if not without_store else None,
        entry_id=config_entry.entry_id,
    )

    @callback
    def add_device(device: dict) -> None:
        """Add device.

        :param device: dict: Device object
        """

        return

    updater.new_device_callback = async_dispatcher_connect(
        hass, SIGNAL_NEW_DEVICE, add_device
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        CONF_IP_ADDRESS: _ip,
        UPDATER: updater,
    }

    return [updater, config_entry]


async def async_mock_luci_client(mock_luci_client) -> None:
    """Mock"""

    mock_luci_client.return_value.logout = AsyncMock(return_value=None)
    mock_luci_client.return_value.login = AsyncMock(
        return_value=json.loads(load_fixture("login_data.json"))
    )
    mock_luci_client.return_value.init_info = AsyncMock(
        return_value=json.loads(load_fixture("init_info_data.json"))
    )
    mock_luci_client.return_value.image = AsyncMock(
        return_value=load_fixture("image_data.txt")
    )
    mock_luci_client.return_value.status = AsyncMock(
        return_value=json.loads(load_fixture("status_data.json"))
    )
    mock_luci_client.return_value.rom_update = AsyncMock(
        return_value=json.loads(load_fixture("rom_update_data.json"))
    )
    mock_luci_client.return_value.mode = AsyncMock(
        return_value=json.loads(load_fixture("mode_data.json"))
    )
    mock_luci_client.return_value.wan_info = AsyncMock(
        return_value=json.loads(load_fixture("wan_info_data.json"))
    )
    mock_luci_client.return_value.led = AsyncMock(
        return_value=json.loads(load_fixture("led_data.json"))
    )
    mock_luci_client.return_value.wifi_connect_devices = AsyncMock(
        return_value=json.loads(load_fixture("wifi_connect_devices_data.json"))
    )
    mock_luci_client.return_value.wifi_detail_all = AsyncMock(
        return_value=json.loads(load_fixture("wifi_detail_all_data.json"))
    )
    mock_luci_client.return_value.wifi_diag_detail_all = AsyncMock(
        return_value=json.loads(load_fixture("wifi_diag_detail_all_data.json"))
    )
    mock_luci_client.return_value.device_list = AsyncMock(
        return_value=json.loads(load_fixture("device_list_data.json"))
    )

    async def mock_avaliable_channels(index: int = 1) -> dict:
        """Mock channels"""

        if index == 2:
            return json.loads(load_fixture("avaliable_channels_5g_data.json"))

        if index == 3:
            return json.loads(load_fixture("avaliable_channels_5g_game_data.json"))

        return json.loads(load_fixture("avaliable_channels_2g_data.json"))

    mock_luci_client.return_value.avaliable_channels = AsyncMock(
        side_effect=mock_avaliable_channels
    )
    mock_luci_client.return_value.new_status = AsyncMock(
        return_value=json.loads(load_fixture("new_status_data.json"))
    )
    mock_luci_client.return_value.wifi_ap_signal = AsyncMock(
        return_value=json.loads(load_fixture("wifi_ap_signal_data.json"))
    )
    mock_luci_client.return_value.topo_graph = AsyncMock(
        return_value=json.loads(load_fixture("topo_graph_data.json"))
    )


def get_url(
    path: str,
    query_params: dict | None = None,
    use_stok: bool = True,
) -> str:
    """Generate url

    :param path: str
    :param query_params: dict | None
    :param use_stok:  bool
    :return: str
    """

    if query_params is not None and len(query_params) > 0:
        path += f"?{urllib.parse.urlencode(query_params, doseq=True)}"

    _stok: str = ";stok=**REDACTED**/" if use_stok else ""

    return f"http://{MOCK_IP_ADDRESS}/cgi-bin/luci/{_stok}api/{path}"


class MultipleSideEffect:  # pylint: disable=too-few-public-methods
    """Multiple side effect"""

    def __init__(self, *fns):
        """init"""

        self.funcs = iter(fns)

    def __call__(self, *args, **kwargs):
        """call"""

        func = next(self.funcs)
        return func(*args, **kwargs)
