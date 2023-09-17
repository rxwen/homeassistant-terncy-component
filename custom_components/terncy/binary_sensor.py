"""Binary sensor platform support for Terncy."""
import logging
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TerncyEntityDescription
from .core.entity import TerncyEntity, create_entity_setup
from .types import AttrValue
from .utils import get_attr_value

if TYPE_CHECKING:
    from .core.gateway import TerncyGateway

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TerncyBinarySensorDescription(
    TerncyEntityDescription, BinarySensorEntityDescription
):
    PLATFORM: Platform = Platform.BINARY_SENSOR
    has_entity_name: bool = True
    value_attr: str = ""
    value_map: dict[int, bool] = field(default_factory=lambda: {1: True, 0: False})


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    def new_entity(gateway, eid: str, description: TerncyEntityDescription):
        return TerncyBinarySensor(gateway, eid, description)

    gw: "TerncyGateway" = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(
        Platform.BINARY_SENSOR, create_entity_setup(async_add_entities, new_entity)
    )


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
