"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.automation import DOMAIN as AUTOMATION_DOMAIN
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
    load_fixture,
)
from pytest_httpx import HTTPXMock

from custom_components.miwifi.const import (
    ATTR_DEVICE_MAC_ADDRESS,
    CONF_BODY,
    CONF_REQUEST,
    CONF_RESPONSE,
    CONF_URI,
    DOMAIN,
    EVENT_TYPE_RESPONSE,
    NAME,
    SERVICE_CALC_PASSWD,
    SERVICE_REQUEST,
    UPDATER,
)
from custom_components.miwifi.exceptions import NotSupportedError
from custom_components.miwifi.updater import LuciUpdater
from tests.setup import MOCK_IP_ADDRESS, async_mock_luci_client, async_setup, get_url

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


@pytest.fixture
def calls(hass):
    """Track calls to a mock service."""
    return async_mock_service(hass, "test", "automation")


async def setup_automation(hass, device_id, trigger_type):
    """Set up an automation trigger for testing triggering."""

    return await async_setup_component(
        hass,
        AUTOMATION_DOMAIN,
        {
            AUTOMATION_DOMAIN: [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_id,
                        "type": trigger_type,
                    },
                    "action": {
                        "service": "test.automation",
                        "data": "{{ trigger.event.data }}",
                    },
                },
            ]
        },
    )


async def test_calc_passwd(hass: HomeAssistant) -> None:
    """Test calc passwd.

    :param hass: HomeAssistant
    """

    def pn_check(hass: HomeAssistant, message: str, title: str) -> None:
        assert title == NAME
        assert message == "Your passwd: 0f2d9073"

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
    ), patch(
        "custom_components.miwifi.services.pn.async_create", side_effect=pn_check
    ):
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        assert await hass.services.async_call(
            DOMAIN,
            SERVICE_CALC_PASSWD,
            {CONF_IP_ADDRESS: MOCK_IP_ADDRESS},
            blocking=True,
            limit=None,
        )


async def test_calc_passwd_incorrect_ip(hass: HomeAssistant) -> None:
    """Test calc passwd incorrect ip.

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

        with pytest.raises(ValueError) as error:
            await hass.services.async_call(
                DOMAIN,
                SERVICE_CALC_PASSWD,
                {CONF_IP_ADDRESS: "127.0.0.1"},
                blocking=True,
                limit=None,
            )

        assert str(error.value) == "Integration with identifier: 127.0.0.1 not found."


async def test_calc_passwd_unsupported(hass: HomeAssistant) -> None:
    """Test calc passwd unsupported.

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
            return_value=json.loads(load_fixture("status_without_version_data.json"))
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        with pytest.raises(NotSupportedError) as error:
            await hass.services.async_call(
                DOMAIN,
                SERVICE_CALC_PASSWD,
                {CONF_IP_ADDRESS: MOCK_IP_ADDRESS},
                blocking=True,
                limit=None,
            )

        assert (
            str(error.value)
            == f"Integration with ip address: {MOCK_IP_ADDRESS} does not support this service."
        )


async def test_request(
    hass: HomeAssistant,
    httpx_mock: HTTPXMock,
    calls,  # pylint: disable=redefined-outer-name
) -> None:
    """Test request.

    :param hass: HomeAssistant
    :param httpx_mock: HTTPXMock
    :param calls
    """

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        text=load_fixture("init_info_data.json"),
        method="GET",
        url=get_url("xqsystem/init_info"),
    )
    httpx_mock.add_response(
        text=load_fixture("status_data.json"),
        method="GET",
        url=get_url("misystem/status"),
    )
    httpx_mock.add_response(
        text=load_fixture("mode_data.json"),
        method="GET",
        url=get_url("xqnetwork/mode"),
    )
    httpx_mock.add_response(
        text=load_fixture("wifi_detail_all_data.json"),
        method="GET",
        url=get_url("xqnetwork/wifi_detail_all"),
    )
    httpx_mock.add_response(
        text=load_fixture("wifi_diag_detail_all_data.json"),
        method="GET",
        url=get_url("xqnetwork/wifi_diag_detail_all"),
    )
    httpx_mock.add_response(
        text=load_fixture("avaliable_channels_2g_data.json"),
        method="GET",
        url=get_url("xqnetwork/avaliable_channels", {"wifiIndex": 1}),
    )
    httpx_mock.add_response(
        text=load_fixture("avaliable_channels_5g_data.json"),
        method="GET",
        url=get_url("xqnetwork/avaliable_channels", {"wifiIndex": 2}),
    )
    httpx_mock.add_response(
        text=load_fixture("wan_info_data.json"),
        method="GET",
        url=get_url("xqnetwork/wan_info"),
    )
    httpx_mock.add_response(
        text=load_fixture("led_data.json"),
        method="GET",
        url=get_url("misystem/led", {}),
    )
    httpx_mock.add_response(
        text=load_fixture("device_list_data.json"),
        method="GET",
        url=get_url("misystem/devicelist"),
    )
    httpx_mock.add_response(
        text=load_fixture("wifi_connect_devices_data.json"),
        method="GET",
        url=get_url("xqnetwork/wifi_connect_devices"),
    )
    httpx_mock.add_response(
        text=load_fixture("rom_update_data.json"),
        method="GET",
        url=get_url("xqsystem/check_rom_update"),
    )
    httpx_mock.add_response(
        text=load_fixture("led_data.json"),
        method="GET",
        url=get_url("misystem/led", {"on": 1}),
    )

    with patch("custom_components.miwifi.updater.async_dispatcher_send"), patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        device_identifier: str = updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip)
        device: dr.DeviceEntry | None = dr.async_get(hass).async_get_device(
            set(),
            {(dr.CONNECTION_NETWORK_MAC, device_identifier)},
        )

        assert device is not None

        assert await setup_automation(hass, device.id, EVENT_TYPE_RESPONSE)
        await hass.async_block_till_done()

        assert await hass.services.async_call(
            DOMAIN,
            SERVICE_REQUEST,
            {
                CONF_IP_ADDRESS: MOCK_IP_ADDRESS,
                CONF_URI: "misystem/led",
                CONF_BODY: {"on": 1},
            },
            blocking=True,
            limit=None,
        )
        await hass.async_block_till_done()

        assert len(calls) == 1

        event_data: dict = calls[0].data

        assert event_data["device_id"] == device.id
        assert event_data[CONF_REQUEST] == {"on": 1}
        assert event_data[CONF_RESPONSE] == {"code": 0, "status": 1}
        assert event_data[CONF_URI] == "misystem/led"
