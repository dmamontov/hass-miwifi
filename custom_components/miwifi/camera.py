"""Camera component."""

from __future__ import annotations

import base64
import logging

from homeassistant.components.camera import (
    ENTITY_ID_FORMAT,
    CameraEntityDescription,
    Camera,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    UPDATER,
    ATTRIBUTION,
    DEFAULT_MANUFACTURER,
    ATTR_DEVICE_MANUFACTURER,
    ATTR_DEVICE_MODEL,
    ATTR_DEVICE_MAC_ADDRESS,
    ATTR_CAMERA_IMAGE,
    ATTR_CAMERA_IMAGE_NAME,
)
from .helper import generate_entity_id
from .updater import LuciUpdater

MIWIFI_CAMERAS: tuple[CameraEntityDescription, ...] = (
    CameraEntityDescription(
        key=ATTR_CAMERA_IMAGE,
        name=ATTR_CAMERA_IMAGE_NAME,
        icon="mdi:image",
        entity_registry_enabled_default=False,
    ),
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MiWifi camera entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: Config Entry object
    :param async_add_entities: AddEntitiesCallback: Async add callback
    """

    data: dict = hass.data[DOMAIN][config_entry.entry_id]
    updater: LuciUpdater = data[UPDATER]

    if not updater.data.get(ATTR_DEVICE_MAC_ADDRESS, False):
        _LOGGER.error("Failed to initialize camera: Missing mac address. Restart HASS.")

    entities: list[MiWifiCamera] = [
        MiWifiCamera(
            f"{config_entry.entry_id}-{description.key}",
            description,
            updater,
        )
        for description in MIWIFI_CAMERAS
    ]
    async_add_entities(entities)


class MiWifiCamera(Camera):
    """MiWifi camera entry."""

    _attr_attribution: str = ATTRIBUTION

    def __init__(
        self,
        unique_id: str,
        description: CameraEntityDescription,
        updater: LuciUpdater,
    ) -> None:
        """Initialize camera.

        :param unique_id: str: Unique ID
        :param description: CameraEntityDescription: CameraEntityDescription object
        :param updater: LuciUpdater: Luci updater object
        """

        super().__init__()

        self.entity_description = description
        self._updater: LuciUpdater = updater

        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            updater.data.get(ATTR_DEVICE_MAC_ADDRESS, updater.ip),
            description.name,
        )

        self._attr_available = updater.data.get(description.key, None) is not None
        self._attr_entity_registry_enabled_default = self._attr_available
        self._attr_is_on = self._attr_available

        self._attr_name = description.name
        self._attr_unique_id = unique_id

        self._attr_brand = updater.data.get(
            ATTR_DEVICE_MANUFACTURER, DEFAULT_MANUFACTURER
        )
        self._attr_model = updater.data.get(ATTR_DEVICE_MODEL, None)

        self._attr_device_info = updater.device_info

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Camera image

        :param width: int | None
        :param height: int | None
        :return bytes
        """

        image: bytes | None = self._updater.data.get(self.entity_description.key, None)

        if image is None:
            return image

        try:
            return base64.b64decode(image)
        except BaseException:
            return None

    def turn_off(self) -> None:
        """Turn off camera."""
        pass

    def turn_on(self) -> None:
        """Turn off camera."""
        pass

    def enable_motion_detection(self) -> None:
        """Enable motion detection in the camera."""
        pass

    def disable_motion_detection(self) -> None:
        """Disable motion detection in camera."""
        pass
