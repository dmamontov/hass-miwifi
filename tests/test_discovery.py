"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines,line-too-long

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import load_fixture

from custom_components.miwifi.const import DOMAIN
from custom_components.miwifi.discovery import async_start_discovery
from custom_components.miwifi.exceptions import LuciConnectionError, LuciError
from tests.setup import MultipleSideEffect, async_mock_luci_client

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


@pytest.mark.asyncio
async def test_discovery(hass: HomeAssistant) -> None:
    """discovery init.

    :param hass: HomeAssistant
    """

    with patch("custom_components.miwifi.discovery.LuciClient") as mock_luci_client:
        await async_mock_luci_client(mock_luci_client)

        async_start_discovery(hass)
        async_start_discovery(hass)
        await hass.async_block_till_done()

        assert len(hass.config_entries.flow._progress) == 2

        for entry_id in hass.config_entries.flow._progress.keys():
            flow = hass.config_entries.flow.async_get(entry_id)

            assert flow["handler"] == DOMAIN
            assert flow["step_id"] == "discovery_confirm"
            assert flow["context"]["unique_id"] in ["192.168.31.1", "192.168.31.62"]
            assert flow["context"]["source"] == "integration_discovery"


@pytest.mark.asyncio
async def test_discovery_sub_leaf(hass: HomeAssistant) -> None:
    """discovery init.

    :param hass: HomeAssistant
    """

    with patch("custom_components.miwifi.discovery.LuciClient") as mock_luci_client:
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.topo_graph = AsyncMock(
            return_value=json.loads(load_fixture("topo_graph_sub_leaf_data.json"))
        )

        async_start_discovery(hass)
        await hass.async_block_till_done()

        assert len(hass.config_entries.flow._progress) == 3

        for entry_id in hass.config_entries.flow._progress.keys():
            flow = hass.config_entries.flow.async_get(entry_id)

            assert flow["handler"] == DOMAIN
            assert flow["step_id"] == "discovery_confirm"
            assert flow["context"]["unique_id"] in [
                "192.168.31.1",
                "192.168.31.62",
                "192.168.31.162",
            ]
            assert flow["context"]["source"] == "integration_discovery"


@pytest.mark.asyncio
async def test_discovery_error(hass: HomeAssistant) -> None:
    """discovery init error.

    :param hass: HomeAssistant
    """

    with patch("custom_components.miwifi.discovery.LuciClient") as mock_luci_client:
        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.topo_graph = AsyncMock(side_effect=LuciError)

        async_start_discovery(hass)
        await hass.async_block_till_done()

        assert len(hass.config_entries.flow._progress) == 0


@pytest.mark.asyncio
async def test_discovery_invalid_device(hass: HomeAssistant) -> None:
    """discovery init.

    :param hass: HomeAssistant
    """

    with patch("custom_components.miwifi.discovery.LuciClient") as mock_luci_client:
        await async_mock_luci_client(mock_luci_client)

        def success() -> dict:
            return json.loads(load_fixture("topo_graph_data.json"))

        def error() -> None:
            raise LuciConnectionError

        def correct_error() -> None:
            raise LuciError

        mock_luci_client.return_value.topo_graph = AsyncMock(
            side_effect=MultipleSideEffect(success, error, correct_error)
        )

        async_start_discovery(hass)
        await hass.async_block_till_done()

        assert len(hass.config_entries.flow._progress) == 1

        for entry_id in hass.config_entries.flow._progress.keys():
            flow = hass.config_entries.flow.async_get(entry_id)

            assert flow["handler"] == DOMAIN
            assert flow["step_id"] == "discovery_confirm"
            assert flow["context"]["unique_id"] == "192.168.31.62"
            assert flow["context"]["source"] == "integration_discovery"
