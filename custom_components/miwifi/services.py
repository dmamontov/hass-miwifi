"""Services."""

from __future__ import annotations

from typing import Final

import hashlib
import logging
import voluptuous as vol

from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ServiceCallType

import homeassistant.components.persistent_notification as pn

from .const import (
    DOMAIN,
    NAME,
    UPDATER,
    CONF_URI,
    CONF_BODY,
    SERVICE_CALC_PASSWD,
    SERVICE_REQUEST,
    ATTR_DEVICE_HW_VERSION,
)
from .exceptions import NotSupportedError
from .luci import LuciClient
from .updater import LuciUpdater

_LOGGER = logging.getLogger(__name__)


class MiWifiServiceCall:
    """Parent class for all MiWifi service calls."""

    schema = vol.Schema({vol.Required(CONF_IP_ADDRESS): str})

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize service call.

        :param hass: HomeAssistant
        """

        self.hass = hass

    def get_updater(self, service: ServiceCallType) -> LuciUpdater:
        """Get updater.

        :param service: ServiceCallType
        :return LuciUpdater
        """

        integrations: dict[str, LuciUpdater] = {
            integration[CONF_IP_ADDRESS]: integration[UPDATER]
            for integration in self.hass.data[DOMAIN].values()
            if isinstance(integration, dict)
        }

        _ip = dict(service.data).get(CONF_IP_ADDRESS)

        if _ip not in integrations:
            raise ValueError(f"Integration with ip address: {_ip} not found.")

        return integrations[_ip]

    async def async_call_service(self, service: ServiceCallType) -> None:
        """Execute service call.

        :param service: ServiceCallType
        """

        raise NotImplementedError  # pragma: no cover


class MiWifiCalcPasswdServiceCall(MiWifiServiceCall):
    """Calculate passwd."""

    salt_old: str = "A2E371B0-B34B-48A5-8C40-A7133F3B5D88"
    salt_new: str = "6d2df50a-250f-4a30-a5e6-d44fb0960aa0"

    async def async_call_service(self, service: ServiceCallType) -> None:
        """Execute service call.

        :param service: ServiceCallType
        """

        _updater: LuciUpdater = self.get_updater(service)

        if hw_version := _updater.data.get(ATTR_DEVICE_HW_VERSION):
            _salt: str = hw_version + (
                self.salt_new if "/" in hw_version else self.salt_old
            )

            pn.async_create(
                self.hass,
                f"Your passwd: {hashlib.md5(_salt.encode()).hexdigest()[0:8]}",
                NAME,
            )

            return

        raise NotSupportedError(
            f"Integration with ip address: {_updater.ip} does not support this service."
        )


class MiWifiRequestServiceCall(MiWifiServiceCall):
    """Send request."""

    schema = MiWifiServiceCall.schema.extend(
        {vol.Required(CONF_URI): str, vol.Optional(CONF_BODY): dict}
    )

    async def async_call_service(self, service: ServiceCallType) -> None:
        """Execute service call.

        :param service: ServiceCallType
        """

        client: LuciClient = self.get_updater(service).luci

        _data: dict = dict(service.data)

        await client.get(_data.get(CONF_URI), _data.get(CONF_BODY, {}))  # type: ignore


SERVICES: Final = (
    (SERVICE_CALC_PASSWD, MiWifiCalcPasswdServiceCall),
    (SERVICE_REQUEST, MiWifiRequestServiceCall),
)
