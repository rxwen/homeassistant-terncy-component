"""Event platform support for Terncy. HA>=2023.8"""

import logging
from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .hass.entity import TerncyEntity
from .hass.entity_descriptions import TerncyEventDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    TerncyEntity.ADD[f"{entry.entry_id}.event"] = async_add_entities


class TerncyEvent(TerncyEntity, EventEntity):
    """Represents a Terncy Button."""

    entity_description: TerncyEventDescription

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if device := self.gateway.parsed_devices.get(self.eid):
            for event_type in self.event_types:
                self.async_on_remove(
                    device.add_event_listener(event_type, self.trigger_event)
                )

    def update_state(self, attrs):
        # _LOGGER.debug("%s <= %s", self.eid, attrs)
        # do nothing
        pass

    def trigger_event(
        self, event_type: str, event_attributes: dict[str, Any] | None = None
    ) -> None:
        self._trigger_event(event_type, event_attributes)
        self.async_write_ha_state()


TerncyEntity.NEW["event"] = TerncyEvent
