"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

from datetime import timedelta
import logging
from unittest.mock import AsyncMock, patch
import json
import pytest
from homeassistant.components.light import (
    ENTITY_ID_FORMAT as LIGHT_ENTITY_ID_FORMAT,
    DOMAIN as LIGHT_DOMAIN,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_ON,
    STATE_OFF,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util.dt import utcnow

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    load_fixture,
    async_fire_time_changed,
)

from custom_components.miwifi.const import (
    DOMAIN,
    UPDATER,
    DEFAULT_SCAN_INTERVAL,
    ATTRIBUTION,
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_LIGHT_LED_NAME,
)
from custom_components.miwifi.exceptions import LuciTokenException
from custom_components.miwifi.helper import generate_entity_id
from custom_components.miwifi.updater import LuciUpdater

from tests.setup import async_mock_luci_client, async_setup, MultipleSideEffect

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_init(hass: HomeAssistant) -> None:
    """Test init.

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

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_LIGHT_LED_NAME, updater)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.name == ATTR_LIGHT_LED_NAME
        assert state.attributes["icon"] == "mdi:led-on"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry is not None
        assert entry.entity_category == EntityCategory.CONFIG


async def test_update_led(hass: HomeAssistant) -> None:
    """Test update led.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        await async_mock_luci_client(mock_luci_client)

        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        def success() -> dict:
            return json.loads(load_fixture("device_list_data.json"))

        def error() -> None:
            raise LuciTokenException

        mock_luci_client.return_value.device_list = AsyncMock(
            side_effect=MultipleSideEffect(success, error, error)
        )

        def success_led(state: int | None = None) -> dict:
            return json.loads(load_fixture("led_data.json"))

        def error_led(state: int | None = None) -> None:
            raise LuciTokenException

        mock_luci_client.return_value.led = AsyncMock(
            side_effect=MultipleSideEffect(
                success_led,
                success_led,
                success_led,
                success_led,
                error_led,
                error_led,
                success_led,
            )
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_LIGHT_LED_NAME, updater)

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        _prev_calls: int = len(mock_luci_client.mock_calls)

        assert await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["icon"] == "mdi:led-on"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 1

        assert await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.attributes["icon"] == "mdi:led-off"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 2

        assert await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["icon"] == "mdi:led-on"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 3

        assert await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.attributes["icon"] == "mdi:led-off"
        assert len(mock_luci_client.mock_calls) == _prev_calls + 4

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE


def _generate_id(code: str, updater: LuciUpdater) -> str:
    """Generate unique id

    :param code: str
    :param updater: LuciUpdater
    :return str
    """

    return generate_entity_id(
        LIGHT_ENTITY_ID_FORMAT,
        updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip),
        code,
    )
