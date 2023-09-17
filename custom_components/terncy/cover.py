"""Cover platform support for Terncy."""
import logging
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from homeassistant.components.cover import (
    ATTR_POSITION,
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
        if self.hass:
            self.async_write_ha_state()

    @property
    def is_closed(self) -> bool | None:
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
