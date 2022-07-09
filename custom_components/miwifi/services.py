"""Services."""

from __future__ import annotations

import hashlib
import logging
from typing import Final

import homeassistant.components.persistent_notification as pn
import voluptuous as vol
from homeassistant.const import CONF_DEVICE_ID, CONF_IP_ADDRESS, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ServiceCallType

from .const import (
    ATTR_DEVICE_HW_VERSION,
    ATTR_DEVICE_MAC_ADDRESS,
    CONF_BODY,
    CONF_REQUEST,
    CONF_RESPONSE,
    CONF_URI,
    EVENT_LUCI,
    EVENT_TYPE_RESPONSE,
    NAME,
    SERVICE_CALC_PASSWD,
    SERVICE_REQUEST,
)
from .updater import LuciUpdater, async_get_updater

_LOGGER = logging.getLogger(__name__)


class MiWifiServiceCall:
    """Parent class for all MiWifi service calls."""

    schema = vol.Schema(
        {
            vol.Required(CONF_DEVICE_ID): vol.All(
                vol.Coerce(list),
                vol.Length(
                    min=1, max=1, msg="The service only supports one device per call."
                ),
            )
        }
    )

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

        device_id: str = dict(service.data).pop(CONF_DEVICE_ID)[0]

        device: dr.DeviceEntry | None = dr.async_get(self.hass).async_get(device_id)

        if device is None:
            raise vol.Invalid(f"Device {device_id} not found.")

        for connection_type, identifier in device.connections:
            if connection_type == CONF_IP_ADDRESS and len(identifier) > 0:
                return async_get_updater(self.hass, identifier)

        raise vol.Invalid(
            f"Device {device_id} does not support the called service. Choose a router with MiWifi support."  # pylint: disable=line-too-long
        )

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

            return pn.async_create(
                self.hass,
                f"Your passwd: {hashlib.md5(_salt.encode()).hexdigest()[:8]}",
                NAME,
            )

        raise vol.Invalid(
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

        updater: LuciUpdater = self.get_updater(service)
        device_identifier: str = updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip)

        _data: dict = dict(service.data)

        response: dict = await updater.luci.get(
            uri := _data.get(CONF_URI), body := _data.get(CONF_BODY, {})  # type: ignore
        )

        device: dr.DeviceEntry | None = dr.async_get(self.hass).async_get_device(
            set(),
            {(dr.CONNECTION_NETWORK_MAC, device_identifier)},
        )

        if device is not None:
            self.hass.bus.async_fire(
                EVENT_LUCI,
                {
                    CONF_DEVICE_ID: device.id,
                    CONF_TYPE: EVENT_TYPE_RESPONSE,
                    CONF_URI: uri,
                    CONF_REQUEST: body,
                    CONF_RESPONSE: response,
                },
            )


SERVICES: Final = (
    (SERVICE_CALC_PASSWD, MiWifiCalcPasswdServiceCall),
    (SERVICE_REQUEST, MiWifiRequestServiceCall),
)
