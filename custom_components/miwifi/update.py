"""Update component."""

from __future__ import annotations

import logging
from typing import Final, Any

from homeassistant.components.update import (
    ENTITY_ID_FORMAT,
    UpdateEntityDescription,
    UpdateEntity,
    UpdateEntityFeature,
    UpdateDeviceClass
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    UPDATER,
    ATTRIBUTION,
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_STATE,
    ATTR_UPDATE_FIRMWARE,
    ATTR_UPDATE_FIRMWARE_NAME,
    ATTR_UPDATE_TITLE,
    ATTR_UPDATE_CURRENT_VERSION,
    ATTR_UPDATE_LATEST_VERSION,
    ATTR_UPDATE_RELEASE_SUMMARY,
    ATTR_UPDATE_RELEASE_URL,
    ATTR_UPDATE_DOWNLOAD_URL,
    ATTR_UPDATE_FILE_SIZE,
    ATTR_UPDATE_FILE_HASH,
)
from .helper import generate_entity_id
from .updater import LuciUpdater

ATTR_CHANGES: Final = [
    ATTR_UPDATE_TITLE,
    ATTR_UPDATE_CURRENT_VERSION,
    ATTR_UPDATE_LATEST_VERSION,
    ATTR_UPDATE_RELEASE_SUMMARY,
    ATTR_UPDATE_RELEASE_URL,
    ATTR_UPDATE_DOWNLOAD_URL,
    ATTR_UPDATE_FILE_SIZE,
    ATTR_UPDATE_FILE_HASH,
]

MAP_FEATURE: Final = {
    ATTR_UPDATE_FIRMWARE: UpdateEntityFeature.RELEASE_NOTES
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

    data: dict = hass.data[DOMAIN][config_entry.entry_id]
    updater: LuciUpdater = data[UPDATER]

    if not updater.last_update_success:
        _LOGGER.error("Failed to initialize update.")

        return

    entities: list[MiWifiUpdate] = []
    for description in MIWIFI_UPDATES:
        if description.key == ATTR_UPDATE_FIRMWARE and len(description.key) == 0:
            continue

        entities.append(
            MiWifiUpdate(
                f"{config_entry.entry_id}-{description.key}",
                description,
                updater,
            )
        )

    if len(entities) > 0:
        async_add_entities(entities)


class MiWifiUpdate(UpdateEntity, CoordinatorEntity):
    """MiWifi update entry."""

    _attr_attribution: str = ATTRIBUTION

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

        CoordinatorEntity.__init__(self, coordinator=updater)

        self.entity_description = description
        self._updater = updater

        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip),
            description.name,
        )

        self._attr_name = description.name
        self._attr_unique_id = unique_id
        self._attr_device_info = updater.device_info

        self._update_data = updater.data.get(description.key, {})

        # fmt: off
        self._attr_available = updater.data.get(ATTR_STATE, False) \
            and len(self._update_data) > 0
        # fmt: on

        self._attr_title = self._update_data.get(
            ATTR_UPDATE_TITLE, None
        )
        self._attr_installed_version = self._update_data.get(
            ATTR_UPDATE_CURRENT_VERSION, None
        )
        self._attr_latest_version = self._update_data.get(
            ATTR_UPDATE_LATEST_VERSION, None
        )
        self._attr_release_summary = self._update_data.get(
            ATTR_UPDATE_RELEASE_SUMMARY, None
        )
        self._attr_release_url = self._update_data.get(
            ATTR_UPDATE_RELEASE_URL, None
        )

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""

        await CoordinatorEntity.async_added_to_hass(self)

    @property
    def available(self) -> bool:
        """Is available

        :return bool: Is available
        """

        return self._attr_available and self.coordinator.last_update_success

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        _update_data: dict[str, Any] = self._updater.data.get(self.entity_description.key, {})

        # fmt: off
        is_available = self._updater.data.get(ATTR_STATE, False) \
            and len(_update_data) > 0
        # fmt: on

        is_update = False
        for attr in ATTR_CHANGES:
            if self._update_data.get(attr, None) != _update_data.get(attr, None):
                is_update = True

                break

        if self._attr_available == is_available and not is_update:  # type: ignore
            return

        self._attr_available = is_available
        self._update_data = _update_data

        self._attr_title = self._update_data.get(
            ATTR_UPDATE_TITLE, None
        )
        self._attr_installed_version = self._update_data.get(
            ATTR_UPDATE_CURRENT_VERSION, None
        )
        self._attr_latest_version = self._update_data.get(
            ATTR_UPDATE_LATEST_VERSION, None
        )
        self._attr_release_summary = self._update_data.get(
            ATTR_UPDATE_RELEASE_SUMMARY, None
        )
        self._attr_release_url = self._update_data.get(
            ATTR_UPDATE_RELEASE_URL, None
        )

        self.async_write_ha_state()
