"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import base64
import logging
import json
from pytest_httpx import HTTPXMock
from httpx import Request, HTTPError
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client

from pytest_homeassistant_custom_component.common import load_fixture, get_fixture_path

from custom_components.miwifi.exceptions import (
    LuciError,
    LuciConnectionError,
    LuciRequestError,
)
from custom_components.miwifi.luci import LuciClient

from tests.setup import get_url, MOCK_IP_ADDRESS

_LOGGER = logging.getLogger(__name__)


async def test_login(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Login test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    assert await client.login() == json.loads(load_fixture("login_data.json"))

    request: Request | None = httpx_mock.get_request()
    assert request is not None
    assert request.url == get_url("xqsystem/login", use_stok=False)
    assert request.method == "POST"
    assert client._token == "**REDACTED**"


async def test_login_error_request(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Login test"""

    httpx_mock.add_exception(exception=HTTPError)  # type: ignore

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    with pytest.raises(LuciConnectionError):
        await client.login()


async def test_login_incorrect_token(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Login test"""

    httpx_mock.add_response(text='{"code": 1}', method="POST")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    with pytest.raises(LuciRequestError):
        await client.login()


async def test_logout_without_token(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Logout test"""

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.logout()

    assert not httpx_mock.get_request()


async def test_logout(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Logout test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text="OK", method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()
    await client.logout()

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert (
        request.url
        == f"http://{MOCK_IP_ADDRESS}/cgi-bin/luci/;stok=**REDACTED**/web/logout"
    )
    assert request.method == "GET"


async def test_logout_error(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Logout test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_exception(exception=HTTPError, method="GET")  # type: ignore

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()
    await client.logout()

    assert client.diagnostics["logout"]["message"] == "Logout error"


async def test_get_without_token(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """get test"""

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    with pytest.raises(LuciRequestError):
        await client.get("misystem/miwifi")

    assert not httpx_mock.get_request()


async def test_get(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """get test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text='{"code": 0}', method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()
    assert await client.get("misystem/miwifi") == {"code": 0}

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("misystem/miwifi")
    assert request.method == "GET"


async def test_get_without_stok(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """get test"""

    httpx_mock.add_response(text='{"code": 0}', method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    assert await client.get("misystem/miwifi", use_stok=False) == {"code": 0}

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("misystem/miwifi", use_stok=False)
    assert request.method == "GET"


async def test_get_error(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """get test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_exception(exception=HTTPError, method="GET")  # type: ignore

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    with pytest.raises(LuciConnectionError):
        await client.get("misystem/miwifi")


async def test_get_error_code(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """get test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text='{"code": 1}', method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    with pytest.raises(LuciRequestError):
        await client.get("misystem/miwifi")

    with pytest.raises(LuciError) as error:
        await client.get("misystem/miwifi", errors={1: "custom errors"})

    assert str(error.value) == "custom errors"


async def test_topo_graph(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """topo_graph test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("topo_graph_data.json"), method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.topo_graph() == json.loads(load_fixture("topo_graph_data.json"))

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("misystem/topo_graph", use_stok=False)
    assert request.method == "GET"


async def test_init_info(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """init_info test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("init_info_data.json"), method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.init_info() == json.loads(load_fixture("init_info_data.json"))

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("xqsystem/init_info")
    assert request.method == "GET"


async def test_status(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """status test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("status_data.json"), method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.status() == json.loads(load_fixture("status_data.json"))

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("misystem/status")
    assert request.method == "GET"


async def test_new_status(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """new_status test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("new_status_data.json"), method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.new_status() == json.loads(load_fixture("new_status_data.json"))

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("misystem/newstatus")
    assert request.method == "GET"


async def test_mode(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """mode test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("mode_data.json"), method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.mode() == json.loads(load_fixture("mode_data.json"))

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("xqnetwork/mode")
    assert request.method == "GET"


async def test_wifi_ap_signal(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """wifi_ap_signal test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("wifi_ap_signal_data.json"), method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.wifi_ap_signal() == json.loads(
        load_fixture("wifi_ap_signal_data.json")
    )

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("xqnetwork/wifiap_signal")
    assert request.method == "GET"


async def test_wifi_detail_all(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """wifi_detail_all test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        text=load_fixture("wifi_detail_all_data.json"), method="GET"
    )

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.wifi_detail_all() == json.loads(
        load_fixture("wifi_detail_all_data.json")
    )

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("xqnetwork/wifi_detail_all")
    assert request.method == "GET"


async def test_wifi_diag_detail_all(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """wifi_diag_detail_all test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        text=load_fixture("wifi_diag_detail_all_data.json"), method="GET"
    )

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.wifi_diag_detail_all() == json.loads(
        load_fixture("wifi_diag_detail_all_data.json")
    )

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("xqnetwork/wifi_diag_detail_all")
    assert request.method == "GET"


async def test_set_wifi(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """set_wifi test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text='{"code": 0}', method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    data: dict = {
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

    assert await client.set_wifi(data) == {"code": 0}

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("xqnetwork/set_wifi", data)
    assert request.method == "GET"


async def test_set_guest_wifi(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """set_guest_wifi test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text='{"code": 0}', method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    data: dict = {
        "encryption": "none",
        "on": 0,
        "pwd": "**REDACTED**",
        "ssid": "**REDACTED**",
    }

    assert await client.set_guest_wifi(data) == {"code": 0}

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("xqnetwork/set_wifi_without_restart", data)
    assert request.method == "GET"


async def test_set_avaliable_channels(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """avaliable_channels test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
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
        text=load_fixture("avaliable_channels_5g_game_data.json"),
        method="GET",
        url=get_url("xqnetwork/avaliable_channels", {"wifiIndex": 3}),
    )

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.avaliable_channels(1) == json.loads(
        load_fixture("avaliable_channels_2g_data.json")
    )

    request: Request | None = httpx_mock.get_request(
        method="GET", url=get_url("xqnetwork/avaliable_channels", {"wifiIndex": 1})
    )
    assert request is not None
    assert request.url == get_url("xqnetwork/avaliable_channels", {"wifiIndex": 1})
    assert request.method == "GET"

    assert await client.avaliable_channels(2) == json.loads(
        load_fixture("avaliable_channels_5g_data.json")
    )

    request = httpx_mock.get_request(
        method="GET", url=get_url("xqnetwork/avaliable_channels", {"wifiIndex": 2})
    )
    assert request is not None
    assert request.url == get_url("xqnetwork/avaliable_channels", {"wifiIndex": 2})
    assert request.method == "GET"

    assert await client.avaliable_channels(3) == json.loads(
        load_fixture("avaliable_channels_5g_game_data.json")
    )

    request = httpx_mock.get_request(
        method="GET", url=get_url("xqnetwork/avaliable_channels", {"wifiIndex": 3})
    )
    assert request is not None
    assert request.url == get_url("xqnetwork/avaliable_channels", {"wifiIndex": 3})
    assert request.method == "GET"


async def test_wan_info(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """wan_info test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("wan_info_data.json"), method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.wan_info() == json.loads(load_fixture("wan_info_data.json"))

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("xqnetwork/wan_info")
    assert request.method == "GET"


async def test_reboot(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """reboot test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text='{"code": 0}', method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.reboot() == {"code": 0}

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("xqsystem/reboot")
    assert request.method == "GET"


async def test_set_led(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """led test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        text=load_fixture("led_data.json"),
        method="GET",
        url=get_url("misystem/led", {}),
    )
    httpx_mock.add_response(
        text=load_fixture("led_data.json"),
        method="GET",
        url=get_url("misystem/led", {"on": 0}),
    )
    httpx_mock.add_response(
        text=load_fixture("led_data.json"),
        method="GET",
        url=get_url("misystem/led", {"on": 1}),
    )

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.led() == json.loads(load_fixture("led_data.json"))

    request: Request | None = httpx_mock.get_request(
        method="GET", url=get_url("misystem/led", {})
    )
    assert request is not None
    assert request.url == get_url("misystem/led", {})
    assert request.method == "GET"

    assert await client.led(0) == json.loads(load_fixture("led_data.json"))

    request = httpx_mock.get_request(
        method="GET", url=get_url("misystem/led", {"on": 0})
    )
    assert request is not None
    assert request.url == get_url("misystem/led", {"on": 0})
    assert request.method == "GET"

    assert await client.led(1) == json.loads(load_fixture("led_data.json"))

    request = httpx_mock.get_request(
        method="GET", url=get_url("misystem/led", {"on": 1})
    )
    assert request is not None
    assert request.url == get_url("misystem/led", {"on": 1})
    assert request.method == "GET"


async def test_device_list(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """device_list test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("device_list_data.json"), method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.device_list() == json.loads(
        load_fixture("device_list_data.json")
    )

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("misystem/devicelist")
    assert request.method == "GET"


async def test_wifi_connect_devices(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """wifi_connect_devices test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        text=load_fixture("wifi_connect_devices_data.json"), method="GET"
    )

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.wifi_connect_devices() == json.loads(
        load_fixture("wifi_connect_devices_data.json")
    )

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("xqnetwork/wifi_connect_devices")
    assert request.method == "GET"


async def test_rom_update(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """rom_update test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("rom_update_data.json"), method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.rom_update() == json.loads(load_fixture("rom_update_data.json"))

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("xqsystem/check_rom_update")
    assert request.method == "GET"


async def test_rom_upgrade(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """rom_upgrade test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text='{"code": 0}', method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    data: dict = {
        "update": True,
    }

    assert await client.rom_upgrade(data) == {"code": 0}

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("xqsystem/upgrade_rom", data)
    assert request.method == "GET"


async def test_flash_permission(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """flash_permission test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text='{"code": 0}', method="GET")

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    await client.login()

    assert await client.flash_permission() == {"code": 0}

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("xqsystem/flash_permission")
    assert request.method == "GET"


async def test_image(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """image test"""

    httpx_mock.add_response(
        content=_get_image_fixture("router_r3600_101.png"), method="GET"
    )

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    _url: str = (
        f"http://{MOCK_IP_ADDRESS}/xiaoqiang/web/img/icons/router_r3600_100_on.png"
    )

    assert await client.image("R3600") == base64.b64encode(
        _get_image_fixture("router_r3600_101.png")
    )

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == _url
    assert request.method == "GET"


async def test_image_error(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """image test"""

    httpx_mock.add_exception(exception=HTTPError("error"), method="GET")  # type: ignore

    client: LuciClient = LuciClient(
        get_async_client(hass, False), f"{MOCK_IP_ADDRESS}/", "test"
    )

    assert await client.image("R3600") is None


def _get_image_fixture(path: str) -> bytes:
    """Get image fixture"""

    return get_fixture_path(path, None).read_bytes()
