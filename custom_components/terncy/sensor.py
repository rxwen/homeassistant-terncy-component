"""Sensor platform support for Terncy."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .hass.entity import TerncyEntity
from .hass.entity_descriptions import TerncySensorDescription
from .utils import get_attr_value

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    TerncyEntity.ADD[f"{entry.entry_id}.sensor"] = async_add_entities


class TerncySensor(TerncyEntity, SensorEntity):
    """Represents a Terncy Sensor"""

    entity_description: TerncySensorDescription

    def update_state(self, attrs):
        """Update terncy state."""
        # _LOGGER.debug("%s <= %s", self.eid, attrs)
        if (
            value := get_attr_value(attrs, self.entity_description.value_attr)
        ) is not None:
            self._attr_native_value = self.entity_description.value_fn(value)
        if self.hass:
            self.async_write_ha_state()


TerncyEntity.NEW["sensor"] = TerncySensor
