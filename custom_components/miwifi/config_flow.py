"""Configuration flows."""

from __future__ import annotations

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import dhcp, ssdp
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from httpx import codes

from .const import (
    DOMAIN,
    UPDATER,
    CONF_STAY_ONLINE,
    CONF_IS_FORCE_LOAD,
    CONF_ACTIVITY_DAYS,
    OPTION_IS_FROM_FLOW,
    DEFAULT_STAY_ONLINE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_ACTIVITY_DAYS,
)
from .discovery import async_start_discovery
from .helper import get_config_value, async_verify_access, async_user_documentation_url

_LOGGER = logging.getLogger(__name__)


class MiWifiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore
    """First time set up flow."""

    _discovered_device: ConfigType | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MiWifiOptionsFlow:
        """Get the options flow for this handler.

        :param config_entry: config_entries.ConfigEntry: Config Entry object
        :return MiWifiOptionsFlow: Options Flow object
        """

        return MiWifiOptionsFlow(config_entry)

    async def async_step_ssdp(self, discovery_info: ssdp.SsdpServiceInfo) -> FlowResult:
        """Handle discovery via ssdp.

        :param discovery_info: ssdp.SsdpServiceInfo: Ssdp Service Info object
        :return FlowResult: Result object
        """

        _LOGGER.debug("Starting discovery via ssdp: %s", discovery_info)

        return await self._async_discovery_handoff()

    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> FlowResult:
        """Handle discovery via dhcp.

        :param discovery_info: dhcp.DhcpServiceInfo: Dhcp Service Info object
        :return FlowResult: Result object
        """

        _LOGGER.debug("Starting discovery via dhcp: %s", discovery_info)

        return await self._async_discovery_handoff()

    async def _async_discovery_handoff(self) -> FlowResult:
        """Ensure discovery is active.

        :return FlowResult: Result object
        """
        # Discovery requires an additional check so we use
        # SSDP and DHCP to tell us to start it so it only
        # runs on networks where miwifi devices are present.

        async_start_discovery(self.hass)

        return self.async_abort(reason="discovery_started")

    async def async_step_integration_discovery(
        self, discovery_info: DiscoveryInfoType
    ) -> FlowResult:
        """Handle discovery via integration.

        :param discovery_info: DiscoveryInfoType: Discovery Info object
        :return FlowResult: Result object
        """

        await self.async_set_unique_id(discovery_info[CONF_IP_ADDRESS])
        self._abort_if_unique_id_configured()

        self._discovered_device = discovery_info

        return await self.async_step_discovery_confirm()

    async def async_step_user(
        self, user_input: ConfigType | None = None, errors: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user.

        :param user_input: ConfigType | None: User data
        :param errors: dict | None: Errors list
        :return FlowResult: Result object
        """

        if errors is None:
            errors = {}

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_IP_ADDRESS): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(
                        CONF_STAY_ONLINE, default=DEFAULT_STAY_ONLINE
                    ): cv.positive_int,
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=10)),
                    vol.Required(
                        CONF_TIMEOUT,
                        default=DEFAULT_TIMEOUT,
                    ): vol.All(vol.Coerce(int), vol.Range(min=10)),
                }
            ),
            errors=errors,
        )

    async def async_step_discovery_confirm(
        self, user_input: ConfigType | None = None
    ) -> FlowResult:
        """Handle a flow initialized by discovery.

        :param user_input: ConfigType | None: User data
        :return FlowResult: Result object
        """

        errors: dict[str, str] = {}

        if user_input is not None:
            if self._discovered_device is None:
                await self.async_set_unique_id(user_input[CONF_IP_ADDRESS])
                self._abort_if_unique_id_configured()

            code: codes = await async_verify_access(
                self.hass,
                user_input[CONF_IP_ADDRESS],
                user_input[CONF_PASSWORD],
                user_input[CONF_TIMEOUT],
            )

            _LOGGER.debug("Verify access code: %s", code)

            if codes.is_success(code):
                return self.async_create_entry(
                    title=user_input[CONF_IP_ADDRESS],
                    data=user_input,
                    options={OPTION_IS_FROM_FLOW: True},
                )

            if code == codes.CONFLICT:
                errors["base"] = "router.not.supported"
            elif code == codes.FORBIDDEN:
                errors["base"] = "password.not_matched"
            else:
                errors["base"] = "ip_address.not_matched"

        if self._discovered_device is None:
            return await self.async_step_user(user_input, errors)

        _ip: str = self._discovered_device[CONF_IP_ADDRESS]

        placeholders: dict[str, str] = {
            "name": _ip,
            "ip_address": _ip,
        }
        self.context["title_placeholders"] = placeholders

        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                **placeholders,
                "local_user_documentation_url": await async_user_documentation_url(
                    self.hass
                ),
            },
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_IP_ADDRESS, default=_ip): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(
                        CONF_STAY_ONLINE, default=DEFAULT_STAY_ONLINE
                    ): cv.positive_int,
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=10)),
                    vol.Required(
                        CONF_TIMEOUT,
                        default=DEFAULT_TIMEOUT,
                    ): vol.All(vol.Coerce(int), vol.Range(min=10)),
                }
            ),
            errors=errors,
        )


class MiWifiOptionsFlow(config_entries.OptionsFlow):
    """Changing options flow."""

    _config_entry: config_entries.ConfigEntry

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow.

        :param config_entry: config_entries.ConfigEntry: Config Entry object
        """

        self._config_entry = config_entry

    async def async_step_init(self, user_input: ConfigType | None = None) -> FlowResult:
        """Manage the options.

        :param user_input: ConfigType | None: User data
        """

        errors: dict[str, str] = {}
        if user_input is not None:
            code: codes = await async_verify_access(
                self.hass,
                user_input[CONF_IP_ADDRESS],
                user_input[CONF_PASSWORD],
                user_input[CONF_TIMEOUT],
            )

            _LOGGER.debug("Verify access code: %s", code)

            if codes.is_success(code):
                return self.async_create_entry(
                    title=user_input[CONF_IP_ADDRESS], data=user_input
                )

            if code == codes.CONFLICT:
                errors["base"] = "router.not.supported"
            elif code == codes.FORBIDDEN:
                errors["base"] = "password.not_matched"
            else:
                errors["base"] = "ip_address.not_matched"

        return self.async_show_form(
            step_id="init", data_schema=self._get_options_schema(), errors=errors
        )

    def _get_options_schema(self) -> vol.Schema:
        """Options schema.

        :return vol.Schema: Options schema
        """

        schema: dict = {
            vol.Required(
                CONF_IP_ADDRESS,
                default=get_config_value(self._config_entry, CONF_IP_ADDRESS, ""),
            ): str,
            vol.Required(
                CONF_PASSWORD,
                default=get_config_value(self._config_entry, CONF_PASSWORD, ""),
            ): str,
            vol.Required(
                CONF_STAY_ONLINE,
                default=get_config_value(
                    self._config_entry, CONF_STAY_ONLINE, DEFAULT_STAY_ONLINE
                ),
            ): cv.positive_int,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=get_config_value(
                    self._config_entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=10)),
            vol.Optional(
                CONF_ACTIVITY_DAYS,
                default=get_config_value(
                    self._config_entry, CONF_ACTIVITY_DAYS, DEFAULT_ACTIVITY_DAYS
                ),
            ): cv.positive_int,
            vol.Optional(
                CONF_TIMEOUT,
                default=get_config_value(
                    self._config_entry, CONF_TIMEOUT, DEFAULT_TIMEOUT
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=10)),
        }

        if (
            DOMAIN not in self.hass.data
            or self._config_entry.entry_id not in self.hass.data[DOMAIN]
            or UPDATER not in self.hass.data[DOMAIN][self._config_entry.entry_id]
            or self.hass.data[DOMAIN][self._config_entry.entry_id][UPDATER].is_repeater
        ):
            schema |= {
                vol.Optional(
                    CONF_IS_FORCE_LOAD,
                    default=get_config_value(
                        self._config_entry, CONF_IS_FORCE_LOAD, False
                    ),
                ): cv.boolean,
            }

        return vol.Schema(schema)
