"""Button component."""

from __future__ import annotations

import logging

from homeassistant.components.button import (
    ENTITY_ID_FORMAT,
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_BUTTON_REBOOT, ATTR_BUTTON_REBOOT_NAME, ATTR_STATE
from .entity import MiWifiEntity
from .exceptions import LuciError
from .updater import LuciUpdater, async_get_updater

PARALLEL_UPDATES = 0

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

    updater: LuciUpdater = async_get_updater(hass, config_entry.entry_id)

    entities: list[MiWifiButton] = [
        MiWifiButton(
            f"{config_entry.entry_id}-{description.key}",
            description,
            updater,
        )
        for description in MIWIFI_BUTTONS
    ]
    async_add_entities(entities)


class MiWifiButton(MiWifiEntity, ButtonEntity):
    """MiWifi button entry."""

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

        MiWifiEntity.__init__(self, unique_id, description, updater, ENTITY_ID_FORMAT)

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
        except LuciError as _e:
            _LOGGER.debug("Reboot error: %r", _e)

    async def async_press(self) -> None:
        """Async press action."""

        if action := getattr(self, f"_{self.entity_description.key}_press"):
            await action()
