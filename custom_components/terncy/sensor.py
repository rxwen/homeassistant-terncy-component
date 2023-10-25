"""Sensor platform support for Terncy."""
import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    # EntityCategory,  # >=2023.3
    LIGHT_LUX,
    PERCENTAGE,
    Platform,
    # UnitOfTemperature,  # >=2022.11
    TEMP_CELSIUS,  # <2022.11
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory  # <2023.3
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, TerncyEntityDescription
from .core.entity import TerncyEntity, create_entity_setup
from .utils import get_attr_value

if TYPE_CHECKING:
    from .core.gateway import TerncyGateway

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TerncySensorDescription(TerncyEntityDescription, SensorEntityDescription):
    PLATFORM: Platform = Platform.SENSOR
    has_entity_name: bool = True
    value_attr: str = ""
    value_fn: Callable[[Any], StateType | date | datetime | Decimal] = lambda x: x


@dataclass(slots=True)
class TemperatureDescription(TerncySensorDescription):
    key: str = "temperature"
    sub_key: str = "temperature"
    device_class: SensorDeviceClass = SensorDeviceClass.TEMPERATURE
    # native_unit_of_measurement: UnitOfTemperature = UnitOfTemperature.CELSIUS
    native_unit_of_measurement: str = TEMP_CELSIUS  # <2022.11
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    suggested_display_precision: int = 1
    value_attr: str = "temperature"
    value_fn: Callable[[Any], StateType | date | datetime | Decimal] = (
        lambda data: data / 10.0
    )
    old_unique_id_suffix: str = "_temptemp"


@dataclass(slots=True)
class HumidityDescription(TerncySensorDescription):
    key: str = "humidity"
    sub_key: str = "humidity"
    device_class: SensorDeviceClass = SensorDeviceClass.HUMIDITY
    native_unit_of_measurement: str = PERCENTAGE
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    suggested_display_precision: int = 0
    value_attr: str = "humidity"
    old_unique_id_suffix: str = "_himidityhumidity"


@dataclass(slots=True)
class IlluminanceDescription(TerncySensorDescription):
    key: str = "illuminance"
    sub_key: str = "illuminance"
    device_class: SensorDeviceClass = SensorDeviceClass.ILLUMINANCE
    native_unit_of_measurement: str = LIGHT_LUX
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    suggested_display_precision: int = 0
    value_attr: str = "luminance"
    old_unique_id_suffix: str = "_illu-illumin"


@dataclass(slots=True)
class BatteryDescription(TerncySensorDescription):
    key: str = "battery"
    sub_key: str = "battery"
    entity_category: EntityCategory = EntityCategory.DIAGNOSTIC
    device_class: SensorDeviceClass = SensorDeviceClass.BATTERY
    native_unit_of_measurement: str = PERCENTAGE
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    suggested_display_precision: int = 0
    value_attr: str = "battery"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    def new_entity(gateway, eid: str, description: TerncyEntityDescription):
        return TerncySensor(gateway, eid, description)

    gw: "TerncyGateway" = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(Platform.SENSOR, create_entity_setup(async_add_entities, new_entity))


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
