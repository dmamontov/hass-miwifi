import logging

import asyncio
import hashlib
import random
import time
import uuid
import json

import aiohttp
import async_timeout

from typing import Optional
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_IP_ADDRESS

from . import exceptions
from .const import (
    DOMAIN,
    BASE_RESOURCE,
    DEFAULT_USERNAME,
    LOGIN_TYPE,
    NONCE_TYPE,
    PUBLIC_KEY,
    DEFAULT_MANUFACTURER,
    CONNECTION_RANGES,
    CONNECTION_TO_SENSOR,
    DEVICES_LIST,
    MODE_MAP,
    DEFAULT_TIMEOUT
)

_LOGGER = logging.getLogger(__name__)

class Luci(object):
    def __init__(
        self,
        hass: HomeAssistant,
        session,
        ip: str,
        password: str,
        options: dict = {}
    ) -> None:
        if ip.endswith("/"):
            ip = ip[:-1]

        self.hass = hass

        self._loop = hass.loop
        self._session = session
        self._ip = ip
        self._token = None

        self.base_url = BASE_RESOURCE.format(ip = ip)
        self.password = password

        self.is_force_load = options["is_force_load"] if "is_force_load" in options else False
        self.timeout = options["timeout"] if "timeout" in options else DEFAULT_TIMEOUT

        self.is_repeater_mode = False

        self._data = {
            "switch": {"reboot": False},
            "light": {"led": False},
            "binary_sensor": {"state": False, "wifi_state": False, "wan_state": False},
            "sensor": {
                "devices": 0, "devices_lan": 0, "devices_5ghz": 0, "devices_2_4ghz": 0, "devices_guest": 0,
                "memory_usage": 0, "mode": "default", "uptime": "0:00:00"
            },
        }

        self._device_data = None
        self._signals = {}

        self._new_devices = []
        self._current_devices = []

        self._devices_list = DEVICES_LIST

    @property
    def data(self):
        return self._data

    @property
    def device_data(self):
        return self._device_data

    def set_state(self, state: bool) -> None:
        self._data["binary_sensor"]["state"] = state

    async def login(self) -> dict:
        nonce = self.generate_nonce()

        try:
            with async_timeout.timeout(self.timeout, loop = self._loop):
                response = await self._session.post(
                    "{}/api/xqsystem/login".format(self.base_url),
                    data = {
                        "username": DEFAULT_USERNAME,
                        "logtype": str(LOGIN_TYPE),
                        "password": self.generate_password_hash(nonce, self.password),
                        "nonce": nonce,
                    }
                )

            data = json.loads(await response.read())
        except asyncio.TimeoutError as e:
            _LOGGER.debug("ERROR MiWifi: Timeout connection error %r", e)
            raise exceptions.LuciConnectionError()
        except aiohttp.ClientError as e:
            _LOGGER.debug("ERROR MiWifi: Connection error %r", e)
            raise exceptions.LuciConnectionError()

        if response.status != 200 or "token" not in data:
             raise exceptions.LuciTokenError()

        self._token = data["token"]

        return data

    async def logout(self) -> None:
        try:
            with async_timeout.timeout(self.timeout, loop = self._loop):
                await self._session.get("{}/;stok={}/web/logout".format(self.base_url, self._token))
        except:
            return

    async def prepare_data(self):
        await self.set_device_data()
        await self.set_entity_data()
        await self.set_devices_list()

    async def set_device_data(self) -> None:
        init_info = await self.init_info()
        status = await self.status()
        model = None

        if "model" in init_info:
            model = init_info["model"]
        elif "hardware" in init_info:
            model = init_info["hardware"]

        self._device_data = {
            "mac": status["hardware"]["mac"],
            "name": init_info["routername"] if "routername" in init_info else None,
            "manufacturer": DEFAULT_MANUFACTURER,
            "model": model,
            "sw_version": init_info["romversion"] if "romversion" in init_info else None,
        }

        self._data["sensor"]["uptime"] = str(timedelta(seconds = int(float(status["upTime"]))))

        if "mem" in status and isinstance(status["mem"], dict) and "usage" in status["mem"]:
            self._data["sensor"]["memory_usage"] = int(float(status["mem"]["usage"]) * 100)
        else:
            del self._data["sensor"]["memory_usage"]

    async def set_entity_data(self) -> None:
        mode = await self.mode()
        wifi_status = await self.wifi_status()
        wan_info = await self.wan_info()
        led = await self.led()

        if self._data["sensor"]["mode"] != "mesh":
            self.is_repeater_mode = mode["mode"] > 0
            self._data["sensor"]["mode"] = MODE_MAP[mode["mode"]] if mode["mode"] in MODE_MAP else "undefined"

        wifi_state = True
        for state in wifi_status["status"]:
            if state["up"] != 1:
                wifi_state = False

        uptime = wan_info["info"]["uptime"] if isinstance(wan_info["info"], dict) and "uptime" in wan_info["info"] else 0

        self._data["light"]["led"] = led["status"] == 1 if "status" in led else False
        self._data["binary_sensor"]["wifi_state"] = wifi_state

        if self.is_repeater_mode:
            if "wan_state" in self._data["binary_sensor"]:
                del self._data["binary_sensor"]["wan_state"]
        else:
            self._data["binary_sensor"]["wan_state"] = uptime > 0

    async def set_devices_list(self) -> None:
        wifi_connect_devices = await self.wifi_connect_devices()
        self._signals = {}

        force_devices = {}

        if "list" in wifi_connect_devices:
            for index, device in enumerate(wifi_connect_devices["list"]):
                self._signals[device["mac"]] = device["signal"]
                force_devices[device["mac"]] = device

        if self.is_repeater_mode and self.is_force_load and len(force_devices) > 0:
            await self.add_devices(force_devices, True)

        if self.is_repeater_mode or DOMAIN not in self.hass.data:
            return

        device_list = await self.device_list()

        if "list" not in device_list or len(device_list["list"]) <= 0:
            if len(self._signals) > 0 and not self.is_repeater_mode:
                self.is_repeater_mode = True
                self._data["sensor"]["mode"] = "mesh"

            return

        device_list = {item['mac']:item for item in device_list["list"]}

        devices_to_ip = {}
        entities_map = await self.get_entities_map()

        for mac in device_list:
            device = device_list[mac]

            if device["parent"] and device["parent"] in device_list and device_list[device["parent"]]["ip"][0]["ip"] in entities_map:
                ip = device_list[device["parent"]]["ip"][0]["ip"]
            else:
                ip = self._ip

            device["connection"] = CONNECTION_RANGES[device["type"]]

            if ip not in devices_to_ip:
                devices_to_ip[ip] = {}

            devices_to_ip[ip][mac] = device

        for ip in devices_to_ip:
            if len(devices_to_ip[ip]) == 0:
                continue

            if ip == self._ip:
                await self.add_devices(devices_to_ip[ip])
            elif not self.hass.data[DOMAIN][entities_map[ip]].api.is_force_load:
                await self.hass.data[DOMAIN][entities_map[ip]].api.add_devices(devices_to_ip[ip])
                await asyncio.sleep(1)
                self.hass.data[DOMAIN][entities_map[ip]].update_devices()

    async def add_devices(self, devices: dict, is_force: bool = False) -> None:
        if not self._device_data:
            return

        sensor_default = {
            "devices": 0,
            "devices_lan": 0,
            "devices_5ghz": 0,
            "devices_2_4ghz": 0,
            "devices_guest": 0,
            "mode": self._data["sensor"]["mode"],
            "uptime": self._data["sensor"]["uptime"]
        }

        if "memory_usage" in self._data["sensor"]:
            sensor_default["memory_usage"] = self._data["sensor"]["memory_usage"]

        if is_force:
            try:
                new_status = await self.new_status()

                if "2g" not in new_status:
                    del sensor_default["devices_2_4ghz"]
                else:
                    sensor_default["devices_2_4ghz"] = new_status["2g"]["online_sta_count"]

                if "5g" not in new_status:
                    del sensor_default["devices_5ghz"]
                else:
                    sensor_default["devices_5ghz"] = new_status["5g"]["online_sta_count"]

                del sensor_default["devices_lan"]
                del sensor_default["devices_guest"]
            except:
                del sensor_default["devices_lan"]
                del sensor_default["devices_5ghz"]
                del sensor_default["devices_2_4ghz"]
                del sensor_default["devices_guest"]

        self._data["sensor"] = sensor_default
        self._data["sensor"]["devices"] = len(devices)

        new_devices = []
        current_devices = []

        for mac in devices:
            devices[mac]["router_mac"] = self._device_data["mac"]
            devices[mac]["signal"] = self._signals[mac] if mac in self._signals else 0

            if "name" not in devices[mac]:
                devices[mac]["name"] = mac

            if mac not in self._devices_list:
                new_devices.append(mac)

            current_devices.append(mac)
            self._devices_list[mac] = devices[mac]

            if "type" in devices[mac]:
                self._data["sensor"][CONNECTION_TO_SENSOR[devices[mac]["type"]]] += 1

        self._new_devices = new_devices
        self._current_devices = current_devices

    async def get_entities_map(self) -> dict:
        entries_map = {}

        for entry_id in dict(self.hass.data[DOMAIN]):
            entries_map[self.hass.data[DOMAIN][entry_id].config_entry.options[CONF_IP_ADDRESS]] = entry_id

        return entries_map

    async def get(self, path: str):
        try:
            with async_timeout.timeout(self.timeout, loop = self._loop):
                response = await self._session.get(
                    "{}/;stok={}/api/{}".format(self.base_url, self._token, path),
                )

            data = json.loads(await response.read())
        except asyncio.TimeoutError as e:
            _LOGGER.debug("ERROR MiWifi: Timeout connection error %r", e)
            raise exceptions.LuciConnectionError()
        except aiohttp.ClientError as e:
            _LOGGER.debug("ERROR MiWifi: Connection error %r", e)
            raise exceptions.LuciConnectionError()

        if "code" not in data or data["code"] > 0:
            _LOGGER.debug("ERROR MiWifi: Token error")
            raise exceptions.LuciTokenError()

        return data

    async def init_info(self) -> dict:
        return await self.get("xqsystem/init_info")

    async def status(self) -> dict:
        return await self.get("misystem/status")

    async def new_status(self) -> dict:
        return await self.get("misystem/newstatus")

    async def mode(self) -> dict:
        return await self.get("xqnetwork/mode")

    async def wifi_status(self) -> dict:
        return await self.get("xqnetwork/wifi_status")

    async def wan_info(self) -> dict:
        return await self.get("xqnetwork/wan_info")

    async def reboot(self) -> dict:
        return await self.get("xqsystem/reboot")

    async def led(self, state: Optional[int] = None) -> dict:
        return await self.get("misystem/led{}".format(f"?on={state}" if state is not None else ""))

    async def device_list(self) -> dict:
        return await self.get("misystem/devicelist")

    async def wifi_connect_devices(self) -> dict:
        return await self.get("xqnetwork/wifi_connect_devices")

    @staticmethod
    def sha1(key: str) -> str:
        return hashlib.sha1(key.encode()).hexdigest()

    @staticmethod
    def get_mac_address() -> str:
        as_hex = f"{uuid.getnode():012x}"

        return ":".join(
            as_hex[i : i + 2] for i in range(0, 12, 2)
        )

    def generate_nonce(self) -> str:
        return "{}_{}_{}_{}".format(
            NONCE_TYPE,
            self.get_mac_address(),
            int(time.time()),
            int(random.random() * 1000)
        )

    def generate_password_hash(self, nonce: str, password: str) -> str:
        return self.sha1(nonce + self.sha1(password + PUBLIC_KEY))
