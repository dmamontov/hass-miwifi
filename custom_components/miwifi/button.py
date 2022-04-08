"""Button component."""

from __future__ import annotations

import logging

from homeassistant.components.button import (
    ENTITY_ID_FORMAT,
    ButtonEntityDescription,
    ButtonEntity,
    ButtonDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    UPDATER,
    ATTRIBUTION,
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_STATE,
    ATTR_BUTTON_REBOOT,
    ATTR_BUTTON_REBOOT_NAME,
)
from .helper import generate_entity_id
from .updater import LuciUpdater

MIWIFI_BUTTONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key=ATTR_BUTTON_REBOOT,
        name=ATTR_BUTTON_REBOOT_NAME,
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=True,
    ),
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MiWifi button entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: Config Entry object
    :param async_add_entities: AddEntitiesCallback: Async add callback
    """

    data: dict = hass.data[DOMAIN][config_entry.entry_id]
    updater: LuciUpdater = data[UPDATER]

    if not updater.data.get(ATTR_DEVICE_MAC_ADDRESS, False):
        _LOGGER.error("Failed to initialize button: Missing mac address. Restart HASS.")

    entities: list[MiWifiButton] = [
        MiWifiButton(
            f"{config_entry.entry_id}-{description.key}",
            description,
            updater,
        )
        for description in MIWIFI_BUTTONS
    ]
    async_add_entities(entities)


class MiWifiButton(ButtonEntity, CoordinatorEntity, RestoreEntity):
    """MiWifi button entry."""

    _attr_attribution: str = ATTRIBUTION

    def __init__(
        self,
        unique_id: str,
        description: ButtonEntityDescription,
        updater: LuciUpdater,
    ) -> None:
        """Initialize button.

        :param unique_id: str: Unique ID
        :param description: ButtonEntityDescription: ButtonEntityDescription object
        :param updater: LuciUpdater: Luci updater object
        """

        CoordinatorEntity.__init__(self, coordinator=updater)
        RestoreEntity.__init__(self)

        self.entity_description = description
        self._updater: LuciUpdater = updater

        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip),
            description.name,
        )

        self._attr_name = description.name
        self._attr_unique_id = unique_id

        self._attr_device_info = updater.device_info

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        is_available: bool = self._updater.data.get(ATTR_STATE, False)

        if self._attr_available == is_available:  # type: ignore
            return

        self._attr_available = is_available

        self.async_write_ha_state()

    async def _reboot_press(self) -> None:
        """Press reboot."""

        try:
            await self._updater.luci.reboot()
        except BaseException:
            pass

    async def async_press(self) -> None:
        """Async press action."""

        action = getattr(self, f"_{self.entity_description.key}_press")

        if action:
            await action()
