"""Cover platform support for Terncy."""
import logging
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntity,
    CoverEntityDescription,
    CoverEntityFeature,  # >=2022.5
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import UndefinedType

from .const import DOMAIN, TerncyEntityDescription
from .core.entity import TerncyEntity, create_entity_setup
from .utils import get_attr_value

if TYPE_CHECKING:
    from .core.gateway import TerncyGateway

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TerncyCoverDescription(TerncyEntityDescription, CoverEntityDescription):
    PLATFORM: Platform = Platform.COVER
    has_entity_name: bool = True
    name: str | UndefinedType | None = None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    def new_entity(gateway, eid: str, description: TerncyEntityDescription):
        return TerncyCover(gateway, eid, description)

    gw: "TerncyGateway" = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(Platform.COVER, create_entity_setup(async_add_entities, new_entity))


K_CURTAIN_PERCENT = "curtainPercent"
K_CURTAIN_MOTOR_STATUS = "curtainMotorStatus"
K_TILT_ANGLE = "tiltAngle"


class TerncyCover(TerncyEntity, CoverEntity):
    """Represents a Terncy Cover."""

    entity_description: TerncyCoverDescription

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.STOP
    )

    def update_state(self, attrs):
        # _LOGGER.debug("%s <= %s", self.eid, attrs)
        if (value := get_attr_value(attrs, K_CURTAIN_PERCENT)) is not None:
            self._attr_current_cover_position = value
        if (motor_status := get_attr_value(attrs, K_CURTAIN_MOTOR_STATUS)) is not None:
            self._attr_is_opening = motor_status == 1
            self._attr_is_closing = motor_status == 2
        if self.hass:
            self.async_write_ha_state()

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed or not."""
        return self._attr_current_cover_position == 0

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        _LOGGER.debug("%s async_open_cover: %s", self.eid, kwargs)
        await self.api.set_attribute(self.eid, K_CURTAIN_PERCENT, 100)
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        _LOGGER.debug("%s async_close_cover: %s", self.eid, kwargs)
        await self.api.set_attribute(self.eid, K_CURTAIN_PERCENT, 0)
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        _LOGGER.debug("%s async_set_cover_position: %s", self.eid, kwargs)
        percent = kwargs[ATTR_POSITION]
        await self.api.set_attribute(self.eid, K_CURTAIN_PERCENT, percent)
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        _LOGGER.debug("%s async_stop_cover: %s", self.eid, kwargs)
        await self.api.set_attribute(self.eid, K_CURTAIN_MOTOR_STATUS, 0)
        self.async_write_ha_state()


class TerncyTiltCover(TerncyCover):
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.STOP
        | CoverEntityFeature.OPEN_TILT
        | CoverEntityFeature.CLOSE_TILT
        | CoverEntityFeature.STOP_TILT
        | CoverEntityFeature.SET_TILT_POSITION
    )

    _tilt_angle: int | None = None  # -90~90

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Return current position of cover tilt.

        None is unknown, 0 is closed, 100 is fully open.
        """
        if self._tilt_angle is None:
            return None
        return 100 - round(abs(self._tilt_angle) / 0.9)

    def update_state(self, attrs):
        # _LOGGER.debug("[%s] <= %s", self.unique_id, attrs)
        if (tilt_angle := get_attr_value(attrs, K_TILT_ANGLE)) is not None:
            self._tilt_angle = tilt_angle
        super().update_state(attrs)

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the cover tilt."""
        _LOGGER.debug("%s async_open_cover_tilt: %s", self.eid, kwargs)
        await self.api.set_attribute(self.eid, K_TILT_ANGLE, 0)

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the cover tilt."""
        _LOGGER.debug("%s async_close_cover_tilt: %s", self.eid, kwargs)
        if self._tilt_angle is not None and self._tilt_angle < 0:
            await self.api.set_attribute(self.eid, K_TILT_ANGLE, -90)
        else:
            await self.api.set_attribute(self.eid, K_TILT_ANGLE, 90)

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Move the cover tilt to a specific position."""
        _LOGGER.debug("%s async_set_cover_tilt_position: %s", self.eid, kwargs)
        tilt_position = kwargs[ATTR_TILT_POSITION]
        if self._tilt_angle is not None and self._tilt_angle < 0:
            tilt_angle = -90 + round(tilt_position * 0.9)
        else:
            tilt_angle = 90 - round(tilt_position * 0.9)
        await self.api.set_attribute(self.eid, K_TILT_ANGLE, tilt_angle)

    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:
        """Stop the cover."""
        _LOGGER.debug("%s async_stop_cover_tilt: %s", self.eid, kwargs)
        await self.api.set_attribute(self.eid, K_CURTAIN_MOTOR_STATUS, 0)
