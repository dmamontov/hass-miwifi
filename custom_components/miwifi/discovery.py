"""The MiWifi integration discovery."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.httpx_client import get_async_client
from httpx import AsyncClient

from .const import (
    CLIENT_ADDRESS,
    CLIENT_ADDRESS_IP,
    DEFAULT_CHECK_TIMEOUT,
    DISCOVERY,
    DISCOVERY_INTERVAL,
    DOMAIN,
)
from .exceptions import LuciConnectionError, LuciError
from .luci import LuciClient

_LOGGER = logging.getLogger(__name__)


@callback
def async_start_discovery(hass: HomeAssistant) -> None:
    """Start discovery.

    :param hass: HomeAssistant: Home Assistant object
    """

    data: dict = hass.data.setdefault(DOMAIN, {})
    if DISCOVERY in data:
        return

    data[DISCOVERY] = True

    async def _async_discovery(*_: Any) -> None:
        """Async discovery

        :param _: Any
        """

        async_trigger_discovery(
            hass, await async_discover_devices(get_async_client(hass, False))
        )

    # Do not block startup since discovery takes 31s or more
    asyncio.create_task(_async_discovery())

    async_track_time_interval(hass, _async_discovery, DISCOVERY_INTERVAL)


async def async_discover_devices(client: AsyncClient) -> list:
    """Discover devices.

    :param client: AsyncClient: Async Client object
    :return list: List found IP
    """

    response: dict = {}

    for address in [CLIENT_ADDRESS, CLIENT_ADDRESS_IP]:
        try:
            response = await LuciClient(client, address).topo_graph()

            break
        except LuciError:
            continue

    if (
        "graph" not in response
        or "ip" not in response["graph"]
        or len(response["graph"]["ip"]) == 0
    ):
        return []

    devices: list = []

    if await async_check_ip_address(client, response["graph"]["ip"].strip()):
        devices.append(response["graph"]["ip"].strip())

    if "leafs" in response["graph"]:
        devices = await async_prepare_leafs(client, devices, response["graph"]["leafs"])

    _LOGGER.debug("Found devices: %s", devices)

    return devices


@callback
def async_trigger_discovery(
    hass: HomeAssistant,
    discovered_devices: list,
) -> None:
    """Trigger config flows for discovered devices.

    :param hass: HomeAssistant: Home Assistant object
    :param discovered_devices: list: Discovered devices
    """

    for device in discovered_devices:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
                data={CONF_IP_ADDRESS: device},
            )
        )


async def async_prepare_leafs(client: AsyncClient, devices: list, leafs: list) -> list:
    """Recursive prepare leafs.

    :param client: AsyncClient: Async Client object
    :param devices: list: ip list
    :param leafs: list: leaf devices
    :return list
    """

    for leaf in leafs:
        if (
            "ip" not in leaf
            or len(leaf["ip"]) == 0
            or "hardware" not in leaf
            or len(leaf["hardware"]) == 0
        ):
            continue

        if await async_check_ip_address(client, leaf["ip"].strip()):
            devices.append(leaf["ip"].strip())

        if "leafs" in leaf and len(leaf["leafs"]) > 0:
            devices = await async_prepare_leafs(client, devices, leaf["leafs"])

    return devices


async def async_check_ip_address(client: AsyncClient, ip_address: str) -> bool:
    """Check ip address

    :param client: AsyncClient: Async Client object
    :param ip_address: str: IP address
    :return bool
    """

    try:
        await LuciClient(client, ip_address, timeout=DEFAULT_CHECK_TIMEOUT).topo_graph()
    except LuciConnectionError:
        return False
    except LuciError:
        pass

    return True
