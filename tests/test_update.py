"""Tests for the miwifi component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import json
import logging
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.update import DOMAIN as UPDATE_DOMAIN
from homeassistant.components.update import ENTITY_ID_FORMAT as UPDATE_ENTITY_ID_FORMAT
from homeassistant.components.update import (
    SERVICE_INSTALL,
    UpdateDeviceClass,
    UpdateEntity,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    load_fixture,
)

from custom_components.miwifi.const import (
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_STATE,
    ATTR_UPDATE_FIRMWARE,
    ATTR_UPDATE_FIRMWARE_NAME,
    ATTRIBUTION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    REPOSITORY,
    UPDATER,
)
from custom_components.miwifi.exceptions import LuciRequestError
from custom_components.miwifi.helper import generate_entity_id
from custom_components.miwifi.update import MAP_NOTES
from custom_components.miwifi.updater import LuciUpdater
from tests.setup import MultipleSideEffect, async_mock_luci_client, async_setup

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


@pytest.mark.asyncio
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
        "custom_components.miwifi.update.asyncio.sleep", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_UPDATE_FIRMWARE_NAME, updater)
        assert hass.states.get(unique_id) is not None
        assert registry.async_get(unique_id) is not None


@pytest.mark.asyncio
async def test_init_unsupported(hass: HomeAssistant) -> None:
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
        "custom_components.miwifi.update.asyncio.sleep", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        mock_luci_client.return_value.rom_update = AsyncMock(
            return_value=json.loads(load_fixture("rom_update_key_error_data.json"))
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_UPDATE_FIRMWARE_NAME, updater)
        assert hass.states.get(unique_id) is None
        assert registry.async_get(unique_id) is None


@pytest.mark.asyncio
async def test_update(hass: HomeAssistant) -> None:
    """Test update.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_dispatcher_send"
    ), patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.update.asyncio.sleep", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_UPDATE_FIRMWARE_NAME, updater)
        state: State = hass.states.get(unique_id)
        entry: er.RegistryEntry | None = registry.async_get(unique_id)

        assert state.state == STATE_OFF
        assert state.attributes["installed_version"] == "3.0.34"
        assert state.attributes["latest_version"] == "3.0.34"
        assert not state.attributes["in_progress"]
        assert state.attributes["release_url"] is None
        assert state.attributes["title"] == "Xiaomi RA67 (XIAOMI RA67)"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["device_class"] == UpdateDeviceClass.FIRMWARE
        assert state.attributes["friendly_name"] == ATTR_UPDATE_FIRMWARE_NAME
        assert entry is not None
        assert entry.entity_category == EntityCategory.CONFIG

        assert (
            state.attributes["entity_picture"]
            == f"https://raw.githubusercontent.com/{REPOSITORY}/main/images/RA67.png"
        )


@pytest.mark.asyncio
async def test_need_update(hass: HomeAssistant) -> None:
    """Test need update.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_dispatcher_send"
    ), patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.update.asyncio.sleep", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        def _off() -> dict:
            return json.loads(load_fixture("rom_update_data.json"))

        def _on() -> dict:
            return json.loads(load_fixture("rom_update_need_data.json"))

        mock_luci_client.return_value.rom_update = AsyncMock(
            side_effect=MultipleSideEffect(_off, _on)
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_UPDATE_FIRMWARE_NAME, updater)

        state: State = hass.states.get(unique_id)
        assert state.state == STATE_OFF

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        entry: er.RegistryEntry | None = registry.async_get(unique_id)

        assert state.state == STATE_ON
        assert state.attributes["installed_version"] == "3.0.34"
        assert state.attributes["latest_version"] == "3.0.35"
        assert not state.attributes["in_progress"]
        assert state.attributes["release_url"] == "https://miwifi.com/changelog"
        assert state.attributes["title"] == "Xiaomi RA67 (XIAOMI RA67)"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert state.attributes["device_class"] == UpdateDeviceClass.FIRMWARE
        assert state.attributes["friendly_name"] == ATTR_UPDATE_FIRMWARE_NAME
        assert entry is not None
        assert entry.entity_category == EntityCategory.CONFIG

        assert (
            state.attributes["entity_picture"]
            == f"https://raw.githubusercontent.com/{REPOSITORY}/main/images/RA67.png"
        )


@pytest.mark.asyncio
async def test_release_notes(hass: HomeAssistant) -> None:
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
        "custom_components.miwifi.update.asyncio.sleep", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_UPDATE_FIRMWARE_NAME, updater)

        component = hass.data[UPDATE_DOMAIN]
        entity: UpdateEntity | None = component.get_entity(unique_id)

        assert entity is not None
        assert await entity.async_release_notes() == MAP_NOTES[ATTR_UPDATE_FIRMWARE]


@pytest.mark.asyncio
async def test_install(hass: HomeAssistant) -> None:
    """Test install.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_dispatcher_send"
    ), patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.update.asyncio.sleep", return_value=None
    ) as mock_asyncio_sleep, patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        def _off() -> dict:
            return json.loads(load_fixture("rom_update_data.json"))

        def _on() -> dict:
            return json.loads(load_fixture("rom_update_need_data.json"))

        mock_luci_client.return_value.rom_update = AsyncMock(
            side_effect=MultipleSideEffect(_off, _off, _on)
        )

        mock_luci_client.return_value.rom_upgrade = AsyncMock(return_value={"code": 0})

        mock_luci_client.return_value.flash_permission = AsyncMock(
            return_value={"code": 0}
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_UPDATE_FIRMWARE_NAME, updater)

        state: State = hass.states.get(unique_id)
        assert state.state == STATE_OFF

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success
        updater.data[ATTR_STATE] = False

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON

        assert await hass.services.async_call(
            UPDATE_DOMAIN,
            SERVICE_INSTALL,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        assert len(mock_asyncio_sleep.mock_calls) == 739


@pytest.mark.asyncio
async def test_install_flash_error(hass: HomeAssistant) -> None:
    """Test install.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_dispatcher_send"
    ), patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.update.asyncio.sleep", return_value=None
    ) as mock_asyncio_sleep, patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        def _off() -> dict:
            return json.loads(load_fixture("rom_update_data.json"))

        def _on() -> dict:
            return json.loads(load_fixture("rom_update_need_data.json"))

        mock_luci_client.return_value.rom_update = AsyncMock(
            side_effect=MultipleSideEffect(_off, _on)
        )

        mock_luci_client.return_value.rom_upgrade = AsyncMock(return_value={"code": 0})

        mock_luci_client.return_value.flash_permission = AsyncMock(
            side_effect=LuciRequestError
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_UPDATE_FIRMWARE_NAME, updater)

        state: State = hass.states.get(unique_id)
        assert state.state == STATE_OFF

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON

        assert await hass.services.async_call(
            UPDATE_DOMAIN,
            SERVICE_INSTALL,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        assert len(mock_asyncio_sleep.mock_calls) == 18


@pytest.mark.asyncio
async def test_install_error(hass: HomeAssistant) -> None:
    """Test install error.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_dispatcher_send"
    ), patch(
        "custom_components.miwifi.async_start_discovery", return_value=None
    ), patch(
        "custom_components.miwifi.update.asyncio.sleep", return_value=None
    ), patch(
        "custom_components.miwifi.device_tracker.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.recv.return_value = AsyncMock(return_value=None)

        await async_mock_luci_client(mock_luci_client)

        def _off() -> dict:
            return json.loads(load_fixture("rom_update_data.json"))

        def _on() -> dict:
            return json.loads(load_fixture("rom_update_need_data.json"))

        mock_luci_client.return_value.rom_update = AsyncMock(
            side_effect=MultipleSideEffect(_off, _on)
        )

        mock_luci_client.return_value.rom_upgrade = AsyncMock(
            side_effect=LuciRequestError
        )

        setup_data: list = await async_setup(hass)

        config_entry: MockConfigEntry = setup_data[1]

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: LuciUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_UPDATE_FIRMWARE_NAME, updater)

        state: State = hass.states.get(unique_id)
        assert state.state == STATE_OFF

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON

        with pytest.raises(HomeAssistantError):
            assert await hass.services.async_call(
                UPDATE_DOMAIN,
                SERVICE_INSTALL,
                {ATTR_ENTITY_ID: [unique_id]},
                blocking=True,
                limit=None,
            )


def _generate_id(
    code: str, updater: LuciUpdater, domain: str = UPDATE_ENTITY_ID_FORMAT
) -> str:
    """Generate unique id

    :param code: str
    :param updater: LuciUpdater
    :param domain: str
    :return str
    """

    return generate_entity_id(
        domain,
        updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip),
        code,
    )
