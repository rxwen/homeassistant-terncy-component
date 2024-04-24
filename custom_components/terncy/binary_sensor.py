"""Binary sensor platform support for Terncy."""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .hass.entity import TerncyEntity
from .hass.entity_descriptions import TerncyBinarySensorDescription
from .types import AttrValue
from .utils import get_attr_value

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    TerncyEntity.ADD[f"{entry.entry_id}.binary_sensor"] = async_add_entities


class TerncyBinarySensor(TerncyEntity, BinarySensorEntity):
    """Represents a Terncy Binary Sensor."""

    entity_description: TerncyBinarySensorDescription

    def update_state(self, attrs: list[AttrValue]):
        """Update terncy state."""
        # _LOGGER.debug("%s <= %s", self.eid, attrs)
        if (
            value := get_attr_value(attrs, self.entity_description.value_attr)
        ) is not None:
            self._attr_is_on = self.entity_description.value_map.get(value)
            if self.hass:
                self.async_write_ha_state()


TerncyEntity.NEW["binary_sensor"] = TerncyBinarySensor
