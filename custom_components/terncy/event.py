"""Event platform support for Terncy. HA>=2023.8"""
import logging
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
    EventEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    EVENT_ENTITY_BUTTON_EVENTS,
    FROZEN_ENTITY_DESCRIPTION,
    TerncyEntityDescription,
)
from .core.entity import TerncyEntity, create_entity_setup

if TYPE_CHECKING:
    from .core.gateway import TerncyGateway

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION)
class TerncyEventDescription(TerncyEntityDescription, EventEntityDescription):
    PLATFORM: Platform = Platform.EVENT
    has_entity_name: bool = True


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION)
class TerncyButtonDescription(TerncyEventDescription):
    key: str = "event_button"
    sub_key: str = "button"
    device_class: EventDeviceClass = EventDeviceClass.BUTTON
    translation_key: str = "button"
    event_types: list[str] = field(
        default_factory=lambda: list(EVENT_ENTITY_BUTTON_EVENTS)
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    def new_entity(gateway, eid: str, description: TerncyEntityDescription):
        return TerncyEvent(gateway, eid, description)

    gw: "TerncyGateway" = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(Platform.EVENT, create_entity_setup(async_add_entities, new_entity))


class TerncyEvent(TerncyEntity, EventEntity):
    """Represents a Terncy Button."""

    entity_description: TerncyEventDescription

    def update_state(self, attrs):
        # _LOGGER.debug("%s <= %s", self.eid, attrs)
        # do nothing
        pass

    def trigger_event(
        self, event_type: str, event_attributes: dict[str, Any] | None = None
    ) -> None:
        self._trigger_event(event_type, event_attributes)
        self.async_write_ha_state()
