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
)
from .exceptions import LuciConnectionException, LuciTokenException

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods
class LuciClient:
    """Luci API Client."""

    ip: str = CLIENT_ADDRESS # pylint: disable=invalid-name

    _client: AsyncClient
    _password: str | None = None
    _timeout: int = DEFAULT_TIMEOUT

    _token: str | None = None
    _url: str

    def __init__(
        self,
        client: AsyncClient,
        ip: str = CLIENT_ADDRESS, # pylint: disable=invalid-name
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
        self.ip = ip # pylint: disable=invalid-name
        self._password = password
        self._timeout = timeout

        self._url = CLIENT_URL.format(ip=ip)

    async def login(self) -> dict:
        """Login method

        :return dict: dict with login data.
        """

        _nonce: str = self.generate_nonce()
        _url: str = f"{self._url}/api/xqsystem/login"

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

            _LOGGER.debug("Successful request %s: %s", _url, response.content)

            _data: dict = json.loads(response.content)
        except (HTTPError, ValueError, TypeError) as _e:
            _LOGGER.debug("Connection error %r", _e)

            raise LuciConnectionException("Connection error") from _e

        if response.status_code != 200 or "token" not in _data:
            raise LuciTokenException("Failed to get token")

        self._token = _data["token"]

        return _data

    async def logout(self) -> None:
        """Logout method"""

        if self._token is None:
            return

        _url: str = f"{self._url}/;stok={self._token}/web/logout"

        try:
            async with self._client as client:
                response: Response = await client.get(_url, timeout=self._timeout)

                _LOGGER.debug("Successful request %s: %s", _url, response.content)
        except (HTTPError, ValueError, TypeError) as _e:
            _LOGGER.debug("Logout error: %r", _e)

    async def get(self, path: str, query_params: dict | None = None, use_stok: bool = True) -> dict:
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

            _LOGGER.debug("Successful request %s: %s", _url, response.content)

            _data: dict = json.loads(response.content)
        except (HTTPError, ValueError, TypeError) as _e:
            _LOGGER.debug("Connection error %r", _e)

            raise LuciConnectionException("Connection error") from _e

        if "code" not in _data or _data["code"] > 0:
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

    async def wifi_turn_on(self, index: int) -> dict:
        """xqnetwork/wifi_up method.

        :param index: int|None: Wifi device index
        :return dict: dict with api data.
        """

        return await self.get("xqnetwork/wifi_up", {"index": index})

    async def wifi_turn_off(self, index: int) -> dict:
        """xqnetwork/wifi_down method.

        :param index: int: Wifi device index
        :return dict: dict with api data.
        """

        return await self.get("xqnetwork/wifi_down", {"index": index})

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

    async def image(self, hardware: str) -> bytes | None:
        """router image  method.

        :return dict: dict with api data.
        """

        hardware = slugify(hardware.lower())
        # fmt: off
        url: str = f"http://{self.ip}/xiaoqiang/web/img/icons/router_{hardware}_100_on.png"
        # fmt: on

        try:
            async with self._client as client:
                response: Response = await client.get(url, timeout=self._timeout)

            _LOGGER.debug("Successful request image %s", url)

            if len(response.content) > 0:
                return base64.b64encode(response.content)
        except HTTPError:
            return None

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
