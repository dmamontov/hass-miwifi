"""Tests for the miwifi component."""

from __future__ import annotations

from typing import Final
import logging
import json
from unittest.mock import AsyncMock, patch
import pytest

from homeassistant import data_entry_flow, config_entries, setup
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
)
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from custom_components.miwifi.const import (
    DOMAIN,
    OPTION_IS_FROM_FLOW,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
)
from custom_components.miwifi.exceptions import (
    LuciConnectionException,
    LuciTokenException,
)

MOCK_IP_ADDRESS: Final = "192.168.31.1"
MOCK_PASSWORD: Final = "**REDACTED**"
OPTIONS_FLOW_EDIT_DATA: Final = {
    CONF_IP_ADDRESS: "127.0.0.1",
    CONF_PASSWORD: "new",
    CONF_TIMEOUT: 15,
    CONF_SCAN_INTERVAL: 55,
}
OPTIONS_FLOW_DATA: Final = {
    CONF_IP_ADDRESS: MOCK_IP_ADDRESS,
    CONF_PASSWORD: MOCK_PASSWORD,
    CONF_TIMEOUT: 10,
    CONF_SCAN_INTERVAL: 50,
}

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_user(hass: HomeAssistant) -> None:
    """Test user config.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "discovery_confirm"

    with patch(
        "custom_components.miwifi.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
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

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {CONF_IP_ADDRESS: MOCK_IP_ADDRESS, CONF_PASSWORD: MOCK_PASSWORD},
        )
        await hass.async_block_till_done()

    assert result_configure["flow_id"] == result_init["flow_id"]
    assert result_configure["title"] == MOCK_IP_ADDRESS
    assert result_configure["data"][CONF_IP_ADDRESS] == MOCK_IP_ADDRESS
    assert result_configure["data"][CONF_PASSWORD] == MOCK_PASSWORD
    assert result_configure["data"][CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL
    assert result_configure["data"][CONF_TIMEOUT] == DEFAULT_TIMEOUT
    assert result_configure["options"][OPTION_IS_FROM_FLOW]

    assert len(mock_async_setup_entry.mock_calls) == 1


async def test_user_ip_error(hass: HomeAssistant) -> None:
    """Test user config ip error.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        mock_luci_client.return_value.logout = AsyncMock(return_value=None)
        mock_luci_client.return_value.login = AsyncMock(
            side_effect=LuciConnectionException
        )

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {CONF_IP_ADDRESS: MOCK_IP_ADDRESS, CONF_PASSWORD: MOCK_PASSWORD},
        )
        await hass.async_block_till_done()

    assert result_configure["errors"] == {"base": "ip_address.not_matched"}
    assert len(mock_luci_client.mock_calls) == 4


async def test_token_error(hass: HomeAssistant) -> None:
    """Test user config token error.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        mock_luci_client.return_value.logout = AsyncMock(return_value=None)
        mock_luci_client.return_value.login = AsyncMock(side_effect=LuciTokenException)

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {CONF_IP_ADDRESS: MOCK_IP_ADDRESS, CONF_PASSWORD: MOCK_PASSWORD},
        )
        await hass.async_block_till_done()

    assert result_configure["errors"] == {"base": "password.not_matched"}
    assert len(mock_luci_client.mock_calls) == 4


async def test_undefined_router(hass: HomeAssistant) -> None:
    """Test user undefined router config.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_self_check", return_value=None
    ) as mock_async_self_check, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        mock_luci_client.return_value.logout = AsyncMock(return_value=None)
        mock_luci_client.return_value.login = AsyncMock(
            return_value=json.loads(load_fixture("login_data.json"))
        )
        mock_luci_client.return_value.init_info = AsyncMock(
            return_value=json.loads(
                load_fixture("init_info_undefined_router_data.json")
            )
        )

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {CONF_IP_ADDRESS: MOCK_IP_ADDRESS, CONF_PASSWORD: MOCK_PASSWORD},
        )
        await hass.async_block_till_done()

    assert result_configure["errors"] == {"base": "router.not.supported"}
    assert len(mock_luci_client.mock_calls) == 5
    assert len(mock_async_self_check.mock_calls) == 1


async def test_undefined_router_without_hardware_info(hass: HomeAssistant) -> None:
    """Test user undefined router without hardware info config.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.pn.async_create", return_value=None
    ) as mock_async_create_pm, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        mock_luci_client.return_value.logout = AsyncMock(return_value=None)
        mock_luci_client.return_value.login = AsyncMock(
            return_value=json.loads(load_fixture("login_data.json"))
        )
        mock_luci_client.return_value.init_info = AsyncMock(
            return_value=json.loads(
                load_fixture("init_info_without_hardware_data.json")
            )
        )

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {CONF_IP_ADDRESS: MOCK_IP_ADDRESS, CONF_PASSWORD: MOCK_PASSWORD},
        )
        await hass.async_block_till_done()

    assert result_configure["errors"] == {"base": "router.not.supported"}
    assert len(mock_luci_client.mock_calls) == 5
    assert len(mock_async_create_pm.mock_calls) == 1


async def test_ssdp(hass: HomeAssistant) -> None:
    """Test ssdp config.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.miwifi.config_flow.async_start_discovery", return_value=None
    ) as mock_async_start_discovery, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        result_init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_SSDP}
        )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result_init["handler"] == DOMAIN
    assert result_init["reason"] == "discovery_started"
    assert len(mock_async_start_discovery.mock_calls) == 1


async def test_dhcp(hass: HomeAssistant) -> None:
    """Test dhcp config.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.miwifi.config_flow.async_start_discovery", return_value=None
    ) as mock_async_start_discovery, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        result_init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_DHCP}
        )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result_init["handler"] == DOMAIN
    assert result_init["reason"] == "discovery_started"
    assert len(mock_async_start_discovery.mock_calls) == 1


async def test_integration_discovery(hass: HomeAssistant) -> None:
    """Test integration_discovery config.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})

    result_init = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data={CONF_IP_ADDRESS: MOCK_IP_ADDRESS},
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "discovery_confirm"


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow.

    :param hass: HomeAssistant
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=OPTIONS_FLOW_DATA,
        options={},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.miwifi.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
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

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        result_init = await hass.config_entries.options.async_init(
            config_entry.entry_id
        )

        assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_init["step_id"] == "init"

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input=OPTIONS_FLOW_EDIT_DATA,
        )

    assert result_save["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert (
        config_entry.options[CONF_IP_ADDRESS] == OPTIONS_FLOW_EDIT_DATA[CONF_IP_ADDRESS]
    )
    assert config_entry.options[CONF_PASSWORD] == OPTIONS_FLOW_EDIT_DATA[CONF_PASSWORD]
    assert config_entry.options[CONF_TIMEOUT] == OPTIONS_FLOW_EDIT_DATA[CONF_TIMEOUT]
    assert (
        config_entry.options[CONF_SCAN_INTERVAL]
        == OPTIONS_FLOW_EDIT_DATA[CONF_SCAN_INTERVAL]
    )
    assert len(mock_async_setup_entry.mock_calls) == 1


async def test_options_flow_ip_error(hass: HomeAssistant) -> None:
    """Test options flow ip error.

    :param hass: HomeAssistant
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=OPTIONS_FLOW_DATA,
        options={},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.miwifi.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        mock_luci_client.return_value.logout = AsyncMock(return_value=None)
        mock_luci_client.return_value.login = AsyncMock(
            side_effect=LuciConnectionException
        )

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        result_init = await hass.config_entries.options.async_init(
            config_entry.entry_id
        )

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input=OPTIONS_FLOW_EDIT_DATA,
        )

    assert result_save["errors"] == {"base": "ip_address.not_matched"}
    assert len(mock_async_setup_entry.mock_calls) == 1
    assert len(mock_luci_client.mock_calls) == 4


async def test_options_flow_token_error(hass: HomeAssistant) -> None:
    """Test options flow token error.

    :param hass: HomeAssistant
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=OPTIONS_FLOW_DATA,
        options={},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.miwifi.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        mock_luci_client.return_value.logout = AsyncMock(return_value=None)
        mock_luci_client.return_value.login = AsyncMock(side_effect=LuciTokenException)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        result_init = await hass.config_entries.options.async_init(
            config_entry.entry_id
        )

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input=OPTIONS_FLOW_EDIT_DATA,
        )

    assert result_save["errors"] == {"base": "password.not_matched"}
    assert len(mock_async_setup_entry.mock_calls) == 1
    assert len(mock_luci_client.mock_calls) == 4


async def test_options_flow_undefined_router(hass: HomeAssistant) -> None:
    """Test options flow undefined router.

    :param hass: HomeAssistant
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=OPTIONS_FLOW_DATA,
        options={},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.miwifi.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.miwifi.updater.LuciClient"
    ) as mock_luci_client, patch(
        "custom_components.miwifi.updater.async_self_check", return_value=None
    ) as mock_async_self_check, patch(
        "custom_components.miwifi.updater.asyncio.sleep", return_value=None
    ):
        mock_luci_client.return_value.logout = AsyncMock(return_value=None)
        mock_luci_client.return_value.login = AsyncMock(
            return_value=json.loads(load_fixture("login_data.json"))
        )
        mock_luci_client.return_value.init_info = AsyncMock(
            return_value=json.loads(
                load_fixture("init_info_undefined_router_data.json")
            )
        )

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        result_init = await hass.config_entries.options.async_init(
            config_entry.entry_id
        )

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input=OPTIONS_FLOW_EDIT_DATA,
        )

    assert result_save["errors"] == {"base": "router.not.supported"}
    assert len(mock_async_setup_entry.mock_calls) == 1
    assert len(mock_async_self_check.mock_calls) == 1
    assert len(mock_luci_client.mock_calls) == 5
