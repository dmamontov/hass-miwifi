import logging
import requests
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_PASSWORD, CONF_TIMEOUT
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .core.const import (
    DOMAIN,
    CONF_LAST_ACTIVITY_DAYS,
    CONF_FORCE_LOAD_REPEATER_DEVICES,
    DEFAULT_TIMEOUT,
    DEFAULT_LAST_ACTIVITY_DAYS
)

from .core import exceptions
from .core.luci import Luci

_LOGGER = logging.getLogger(__name__)

AUTH_SCHEMA = vol.Schema({
    vol.Required(CONF_IP_ADDRESS): str,
    vol.Required(CONF_PASSWORD): str
})

class MiWifiFlowHandler(ConfigFlow, domain = DOMAIN):
    async def async_step_import(self, data: dict):
        await self.async_set_unique_id(data[CONF_IP_ADDRESS])
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title = data[CONF_IP_ADDRESS], data = data)

    async def async_step_user(self, user_input = None):
        return self.async_show_form(step_id = 'auth', data_schema = AUTH_SCHEMA)

    async def async_step_auth(self, user_input):
        if user_input is None:
            return self.cur_step

        session = async_get_clientsession(self.hass, False)

        client = Luci(self.hass, session, user_input[CONF_IP_ADDRESS], user_input[CONF_PASSWORD])

        try:
            await client.login()
        except exceptions.LuciConnectionError as e:
            return await self._prepare_error('ip_address.not_matched', e)
        except exceptions.LuciTokenError as e:
            return await self._prepare_error('password.not_matched', e)

        entry = await self.async_set_unique_id(user_input[CONF_IP_ADDRESS])

        if entry:
            self.hass.config_entries.async_update_entry(entry, data = user_input)

            return self.async_abort(reason = 'account_updated')

        return self.async_create_entry(title = user_input[CONF_IP_ADDRESS], data = user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return OptionsFlowHandler(config_entry)

    async def _prepare_error(self, code: str, err):
        _LOGGER.error("Error setting up MiWiFi API: %r", err)

        return self.async_show_form(
            step_id = 'auth',
            data_schema = AUTH_SCHEMA,
            errors = {'base': code}
        )

class OptionsFlowHandler(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input = None):
        return await self.async_step_settings()

    async def async_step_settings(self, user_input = None):
        options_schema = vol.Schema({
            vol.Required(CONF_IP_ADDRESS, default = self.config_entry.options.get(CONF_IP_ADDRESS, "")): str,
            vol.Required(CONF_PASSWORD, default = self.config_entry.options.get(CONF_PASSWORD, "")): str,
            vol.Optional(
                CONF_TIMEOUT,
                default = self.config_entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
            ): cv.positive_int,
            vol.Optional(
                CONF_FORCE_LOAD_REPEATER_DEVICES,
                default = self.config_entry.options.get(CONF_FORCE_LOAD_REPEATER_DEVICES, False)
            ): cv.boolean,
            vol.Optional(
                CONF_LAST_ACTIVITY_DAYS,
                default = self.config_entry.options.get(CONF_LAST_ACTIVITY_DAYS, DEFAULT_LAST_ACTIVITY_DAYS)
            ): cv.positive_int
        })

        if user_input:
            session = async_get_clientsession(self.hass, False)

            client = Luci(self.hass, session, user_input[CONF_IP_ADDRESS], user_input[CONF_PASSWORD])

            try:
                await client.login()
            except exceptions.LuciConnectionError as e:
                return await self._prepare_error('ip_address.not_matched', e, options_schema)
            except exceptions.LuciTokenError as e:
                return await self._prepare_error('password.not_matched', e, options_schema)

            return self.async_create_entry(title = '', data = user_input)

        return self.async_show_form(step_id = "settings", data_schema = options_schema)

    async def _prepare_error(self, code: str, err, options_schema):
        _LOGGER.error("Error setting up MiWiFi API: %r", err)

        return self.async_show_form(
            step_id = 'settings',
            data_schema = options_schema,
            errors = {'base': code}
        )
