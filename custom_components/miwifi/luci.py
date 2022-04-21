"""Luci API Client."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import random
import time
import uuid
import urllib.parse

from datetime import datetime
from typing import Any
from httpx import AsyncClient, Response, HTTPError

from homeassistant.util import slugify

from .const import (
    DEFAULT_TIMEOUT,
    CLIENT_ADDRESS,
    CLIENT_URL,
    CLIENT_USERNAME,
    CLIENT_LOGIN_TYPE,
    CLIENT_NONCE_TYPE,
    CLIENT_PUBLIC_KEY,
    DIAGNOSTIC_DATE_TIME,
    DIAGNOSTIC_MESSAGE,
    DIAGNOSTIC_CONTENT,
)
from .exceptions import LuciConnectionException, LuciTokenException

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods
class LuciClient:
    """Luci API Client."""

    ip: str = CLIENT_ADDRESS  # pylint: disable=invalid-name

    _client: AsyncClient
    _password: str | None = None
    _timeout: int = DEFAULT_TIMEOUT

    _token: str | None = None
    _url: str

    def __init__(
        self,
        client: AsyncClient,
        ip: str = CLIENT_ADDRESS,  # pylint: disable=invalid-name
        password: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize API client.

        :param client: AsyncClient: AsyncClient object
        :param ip: str: device ip address
        :param password: str: device password
        :param timeout: int: Query execution timeout
        """

        if ip.endswith("/"):
            ip = ip[:-1]

        self._client = client
        self.ip = ip  # pylint: disable=invalid-name
        self._password = password
        self._timeout = timeout

        self._url = CLIENT_URL.format(ip=ip)

        self.diagnostics: dict[str, Any] = {}

    async def login(self) -> dict:
        """Login method

        :return dict: dict with login data.
        """

        _method: str = "xqsystem/login"
        _nonce: str = self.generate_nonce()
        _url: str = f"{self._url}/api/{_method}"

        try:
            async with self._client as client:
                response: Response = await client.post(
                    _url,
                    data={
                        "username": CLIENT_USERNAME,
                        "logtype": str(CLIENT_LOGIN_TYPE),
                        "password": self.generate_password_hash(
                            _nonce, str(self._password)
                        ),
                        "nonce": _nonce,
                    },
                    timeout=self._timeout,
                )

            self._debug("Successful request", _url, response.content, _method)

            _data: dict = json.loads(response.content)
        except (HTTPError, ValueError, TypeError) as _e:
            self._debug("Connection error", _url, _e, _method)

            raise LuciConnectionException("Connection error") from _e

        if response.status_code != 200 or "token" not in _data:
            self._debug("Failed to get token", _url, _data, _method)

            raise LuciTokenException("Failed to get token")

        self._token = _data["token"]

        return _data

    async def logout(self) -> None:
        """Logout method"""

        if self._token is None:
            return

        _method: str = "logout"
        _url: str = f"{self._url}/;stok={self._token}/web/{_method}"

        try:
            async with self._client as client:
                response: Response = await client.get(_url, timeout=self._timeout)

                self._debug("Successful request", _url, response.content, _method)
        except (HTTPError, ValueError, TypeError) as _e:
            self._debug("Logout error", _url, _e, _method)

    async def get(
        self, path: str, query_params: dict | None = None, use_stok: bool = True
    ) -> dict:
        """GET method.

        :param path: str: api method
        :param query_params: dict | None: Data
        :param use_stok: bool: is use stack
        :return dict: dict with api data.
        """

        if query_params is not None and len(query_params) > 0:
            path += f"?{urllib.parse.urlencode(query_params, doseq=True)}"

        _stok: str = f";stok={self._token}/" if use_stok else ""
        _url: str = f"{self._url}/{_stok}api/{path}"

        try:
            async with self._client as client:
                response: Response = await client.get(_url, timeout=self._timeout)

            self._debug("Successful request", _url, response.content, path)

            _data: dict = json.loads(response.content)
        except (HTTPError, ValueError, TypeError) as _e:
            self._debug("Connection error", _url, _e, path)

            raise LuciConnectionException("Connection error") from _e

        if "code" not in _data or _data["code"] > 0:
            self._debug("Invalid error code received", _url, _data, path)

            raise LuciTokenException("Invalid error code received")

        return _data

    async def topo_graph(self) -> dict:
        """misystem/topo_graph method.

        :return dict: dict with api data.
        """

        return await self.get("misystem/topo_graph", use_stok=False)

    async def init_info(self) -> dict:
        """xqsystem/init_info method.

        :return dict: dict with api data.
        """

        return await self.get("xqsystem/init_info")

    async def status(self) -> dict:
        """misystem/status method.

        :return dict: dict with api data.
        """

        return await self.get("misystem/status")

    async def new_status(self) -> dict:
        """misystem/newstatus method.

        :return dict: dict with api data.
        """

        return await self.get("misystem/newstatus")

    async def mode(self) -> dict:
        """xqnetwork/mode method.

        :return dict: dict with api data.
        """

        return await self.get("xqnetwork/mode")

    async def wifi_status(self) -> dict:
        """xqnetwork/wifi_status method.

        :return dict: dict with api data.
        """

        return await self.get("xqnetwork/wifi_status")

    async def wifi_ap_signal(self) -> dict:
        """xqnetwork/wifiap_signal method.

        :return dict: dict with api data.
        """

        return await self.get("xqnetwork/wifiap_signal")

    async def wifi_detail_all(self) -> dict:
        """xqnetwork/wifi_detail_all method.

        :return dict: dict with api data.
        """

        return await self.get("xqnetwork/wifi_detail_all")

    async def set_wifi(self, data: dict) -> dict:
        """xqnetwork/set_wifi method.

        :param data: dict: Adapter data
        :return dict: dict with api data.
        """

        return await self.get("xqnetwork/set_wifi", data)

    async def avaliable_channels(self, index: int = 1) -> dict:
        """xqnetwork/avaliable_channels method.

        :param index: int: Index wifi adapter
        :return dict: dict with api data.
        """

        return await self.get("xqnetwork/avaliable_channels", {"wifiIndex": index})

    async def wan_info(self) -> dict:
        """xqnetwork/wan_info method.

        :return dict: dict with api data.
        """

        return await self.get("xqnetwork/wan_info")

    async def reboot(self) -> dict:
        """xqsystem/reboot method.

        :return dict: dict with api data.
        """

        return await self.get("xqsystem/reboot")

    async def led(self, state: int | None = None) -> dict:
        """misystem/led method.

        :param state: int|None: on/off state
        :return dict: dict with api data.
        """

        data: dict = {}
        if state is not None:
            data["on"] = state

        return await self.get("misystem/led", data)

    async def device_list(self) -> dict:
        """misystem/devicelist method.

        :return dict: dict with api data.
        """

        return await self.get("misystem/devicelist")

    async def wifi_connect_devices(self) -> dict:
        """xqnetwork/wifi_connect_devices method.

        :return dict: dict with api data.
        """

        return await self.get("xqnetwork/wifi_connect_devices")

    async def rom_update(self) -> dict:
        """xqsystem/check_rom_update method.

        :return dict: dict with api data.
        """

        return await self.get("xqsystem/check_rom_update")

    async def rom_upgrade(self, data: dict) -> dict:
        """xqsystem/upgrade_rom method.

        :param data: dict: Rom data
        :return dict: dict with api data.
        """

        return await self.get("xqsystem/upgrade_rom", data)

    async def image(self, hardware: str) -> bytes | None:
        """router image  method.

        :return dict: dict with api data.
        """

        hardware = slugify(hardware.lower())
        _path: str = f"icons/router_{hardware}_100_on.png"
        _url: str = f"http://{self.ip}/xiaoqiang/web/img/{_path}"

        try:
            async with self._client as client:
                response: Response = await client.get(_url, timeout=self._timeout)

            self._debug("Successful request image", _url, response.status_code, _path)

            if len(response.content) > 0:
                return base64.b64encode(response.content)
        except HTTPError as _e:
            self._debug("Error request image", _url, _e, _path)

        return None

    @staticmethod
    def sha1(key: str) -> str:
        """Generate sha1 by key.

        :param key: str: the key from which to get the hash
        :return str: sha1 from key.
        """

        return hashlib.sha1(key.encode()).hexdigest()

    @staticmethod
    def get_mac_address() -> str:
        """Generate fake mac address.

        :return str: mac address.
        """

        as_hex: str = f"{uuid.getnode():012x}"

        return ":".join(as_hex[i : i + 2] for i in range(0, 12, 2))

    def generate_nonce(self) -> str:
        """Generate fake nonce.

        :return str: nonce.
        """

        rand: str = f"{int(time.time())}_{int(random.random() * 1000)}"

        return f"{CLIENT_NONCE_TYPE}_{self.get_mac_address()}_{rand}"

    def generate_password_hash(self, nonce: str, password: str) -> str:
        """Generate password hash.

        :param nonce: str: nonce
        :param password: str: password
        :return str: sha1 from password and nonce.
        """

        return self.sha1(nonce + self.sha1(password + CLIENT_PUBLIC_KEY))

    def _debug(self, message: str, url: str, content: Any, path: str) -> None:
        """Debug log

        :param message: str: Message
        :param url: str: URL
        :param content: Any: Content
        :param path: str: Path
        """

        _LOGGER.debug("%s (%s): %s", message, url, str(content))

        _content: dict | str = {}

        try:
            _content = json.loads(content)
        except (ValueError, TypeError):
            _content = str(content)

        self.diagnostics[path] = {
            DIAGNOSTIC_DATE_TIME: datetime.now().replace(microsecond=0).isoformat(),
            DIAGNOSTIC_MESSAGE: message,
            DIAGNOSTIC_CONTENT: _content,
        }
