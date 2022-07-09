"""Update component."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Final

from homeassistant.components.update import (
    ATTR_IN_PROGRESS,
    ENTITY_ID_FORMAT,
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_MODEL,
    ATTR_STATE,
    ATTR_UPDATE_CURRENT_VERSION,
    ATTR_UPDATE_DOWNLOAD_URL,
    ATTR_UPDATE_FILE_HASH,
    ATTR_UPDATE_FILE_SIZE,
    ATTR_UPDATE_FIRMWARE,
    ATTR_UPDATE_FIRMWARE_NAME,
    ATTR_UPDATE_LATEST_VERSION,
    ATTR_UPDATE_RELEASE_URL,
    ATTR_UPDATE_TITLE,
    REPOSITORY,
)
from .entity import MiWifiEntity
from .enum import Model
from .exceptions import LuciError
from .updater import LuciUpdater, async_get_updater

PARALLEL_UPDATES = 0

FIRMWARE_UPDATE_WAIT: Final = 180
FIRMWARE_UPDATE_RETRY: Final = 721

ATTR_CHANGES: Final = (
    ATTR_UPDATE_TITLE,
    ATTR_UPDATE_CURRENT_VERSION,
    ATTR_UPDATE_LATEST_VERSION,
    ATTR_UPDATE_RELEASE_URL,
    ATTR_UPDATE_DOWNLOAD_URL,
    ATTR_UPDATE_FILE_SIZE,
    ATTR_UPDATE_FILE_HASH,
)

MAP_FEATURE: Final = {
    ATTR_UPDATE_FIRMWARE: UpdateEntityFeature.INSTALL
    | UpdateEntityFeature.RELEASE_NOTES
}

MAP_NOTES: Final = {
    ATTR_UPDATE_FIRMWARE: "\n\n<ha-alert alert-type='warning'>"
    + "The firmware update takes an average of 3 to 15 minutes."
    + "</ha-alert>\n\n"
}

MIWIFI_UPDATES: tuple[UpdateEntityDescription, ...] = (
    UpdateEntityDescription(
        key=ATTR_UPDATE_FIRMWARE,
        name=ATTR_UPDATE_FIRMWARE_NAME,
        device_class=UpdateDeviceClass.FIRMWARE,
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
    """Set up MiWifi update entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: ConfigEntry object
    :param async_add_entities: AddEntitiesCallback: AddEntitiesCallback callback object
    """

    updater: LuciUpdater = async_get_updater(hass, config_entry.entry_id)

    entities: list[MiWifiUpdate] = [
        MiWifiUpdate(
            f"{config_entry.entry_id}-{description.key}",
            description,
            updater,
        )
        for description in MIWIFI_UPDATES
        if description.key != ATTR_UPDATE_FIRMWARE or updater.supports_update
    ]

    if entities:
        async_add_entities(entities)


class MiWifiUpdate(MiWifiEntity, UpdateEntity):
    """MiWifi update entry."""

    _update_data: dict[str, Any]

    def __init__(
        self,
        unique_id: str,
        description: UpdateEntityDescription,
        updater: LuciUpdater,
    ) -> None:
        """Initialize update.

        :param unique_id: str: Unique ID
        :param description: UpdateEntityDescription: UpdateEntityDescription object
        :param updater: LuciUpdater: Luci updater object
        """

        MiWifiEntity.__init__(self, unique_id, description, updater, ENTITY_ID_FORMAT)

        if description.key in MAP_FEATURE:
            self._attr_supported_features = MAP_FEATURE[description.key]

        self._update_data = updater.data.get(description.key, {})

        self._attr_available = (
            updater.data.get(ATTR_STATE, False) and len(self._update_data) > 0
        )

        self._attr_title = self._update_data.get(ATTR_UPDATE_TITLE, None)
        self._attr_installed_version = self._update_data.get(
            ATTR_UPDATE_CURRENT_VERSION, None
        )
        self._attr_latest_version = self._update_data.get(
            ATTR_UPDATE_LATEST_VERSION, None
        )
        self._attr_release_url = self._update_data.get(ATTR_UPDATE_RELEASE_URL, None)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""

        await MiWifiEntity.async_added_to_hass(self)

    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture to use in the frontend."""

        model: Model = self._updater.data.get(ATTR_MODEL, Model.NOT_KNOWN)

        return f"https://raw.githubusercontent.com/{REPOSITORY}/main/images/{model.name}.png"

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        if self.state_attributes.get(ATTR_IN_PROGRESS, False):
            return  # pragma: no cover

        _update_data: dict[str, Any] = self._updater.data.get(
            self.entity_description.key, {}
        )

        is_available: bool = (
            self._updater.data.get(ATTR_STATE, False) and len(_update_data) > 0
        )

        attr_changed: list = [
            attr
            for attr in ATTR_CHANGES
            if self._update_data.get(attr, None) != _update_data.get(attr, None)
        ]

        if self._attr_available == is_available and not attr_changed:  # type: ignore
            return

        self._attr_available = is_available
        self._update_data = _update_data

        self._attr_title = self._update_data.get(ATTR_UPDATE_TITLE)
        self._attr_installed_version = self._update_data.get(
            ATTR_UPDATE_CURRENT_VERSION
        )

        self._attr_latest_version = self._update_data.get(ATTR_UPDATE_LATEST_VERSION)
        self._attr_release_url = self._update_data.get(ATTR_UPDATE_RELEASE_URL)

        self.async_write_ha_state()

    async def _firmware_install(self) -> None:
        """Install firmware"""

        try:
            await self._updater.luci.rom_upgrade(
                {
                    "url": self._update_data.get(ATTR_UPDATE_DOWNLOAD_URL),
                    "filesize": self._update_data.get(ATTR_UPDATE_FILE_SIZE),
                    "hash": self._update_data.get(ATTR_UPDATE_FILE_HASH),
                    "needpermission": 1,
                }
            )
        except LuciError as _e:
            raise HomeAssistantError(str(_e)) from _e

        try:
            await self._updater.luci.flash_permission()
        except LuciError as _e:
            _LOGGER.debug("Clear permission error: %r", _e)

        await asyncio.sleep(FIRMWARE_UPDATE_WAIT)

        for _retry in range(1, FIRMWARE_UPDATE_RETRY):
            if self._updater.data.get(ATTR_STATE, False):
                break

            await asyncio.sleep(1)

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install an update.

        :param version: str | None
        :param backup: bool
        :param kwargs: Any: Any arguments
        """

        if action := getattr(self, f"_{self.entity_description.key}_install"):
            await action()

            self._attr_installed_version = self._attr_latest_version

            self.async_write_ha_state()

    async def async_release_notes(self) -> str | None:
        """Release notes

        :return str | None: Notes
        """

        return MAP_NOTES[self.entity_description.key]
