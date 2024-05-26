from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.climate import ClimateEntityDescription
from homeassistant.components.cover import CoverEntityDescription
from homeassistant.components.event import EventDeviceClass, EventEntityDescription
from homeassistant.components.light import (
    ColorMode,
    LightEntityDescription,
    LightEntityFeature,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import (
    EntityCategory,
    LIGHT_LUX,
    MAJOR_VERSION,
    PERCENTAGE,
    Platform,
    UnitOfTemperature,
)
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.typing import StateType, UndefinedType

from ..const import EVENT_ENTITY_BUTTON_EVENTS


# https://developers.home-assistant.io/blog/2023/12/11/entity-description-changes
FROZEN_ENTITY_DESCRIPTION = MAJOR_VERSION >= 2024


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION, kw_only=True)
class TerncyEntityDescription(EntityDescription):
    PLATFORM: Platform = None

    has_entity_name: bool = True

    sub_key: str | None = None
    """用作 unique_id 的后缀。"""

    unique_id_prefix: str | None = None
    """用作 unique_id 的前缀。（目前只给scene用，考虑有没有更好的方式）"""

    old_unique_id_suffix: str | None = None  # use for migrate

    translation_key: str | None = None  # <2023.1 需要这一行，避免报错

    required_attrs: list[str] | None = None
    """需要的属性，如果没有这些属性，就不创建实体"""


# region Binary Sensor


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION, kw_only=True)
class TerncyBinarySensorDescription(
    TerncyEntityDescription, BinarySensorEntityDescription
):
    PLATFORM: Platform = Platform.BINARY_SENSOR
    value_attr: str = ""
    value_map: dict[int, bool] = field(
        default_factory=lambda: {4: True, 3: True, 2: True, 1: True, 0: False}
    )


# endregion

# region Climate


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION, kw_only=True)
class TerncyClimateDescription(TerncyEntityDescription, ClimateEntityDescription):
    PLATFORM: Platform = Platform.CLIMATE
    name: str | UndefinedType | None = None


# endregion

# region Cover


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION, kw_only=True)
class TerncyCoverDescription(TerncyEntityDescription, CoverEntityDescription):
    PLATFORM: Platform = Platform.COVER
    name: str | UndefinedType | None = None


# endregion

# region Event


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION, kw_only=True)
class TerncyEventDescription(TerncyEntityDescription, EventEntityDescription):
    PLATFORM: Platform = Platform.EVENT


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION, kw_only=True)
class TerncyButtonDescription(TerncyEventDescription):
    key: str = "event_button"
    sub_key: str = "button"
    device_class: EventDeviceClass = EventDeviceClass.BUTTON
    translation_key: str = "button"
    event_types: list[str] = field(
        default_factory=lambda: list(EVENT_ENTITY_BUTTON_EVENTS)
    )


# endregion

# region Light


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION, kw_only=True)
class TerncyLightDescription(TerncyEntityDescription, LightEntityDescription):
    key: str = "light"
    PLATFORM: Platform = Platform.LIGHT
    name: str | UndefinedType | None = None
    color_mode: ColorMode | None = None
    supported_color_modes: set[ColorMode] | None = None
    supported_features: LightEntityFeature = 0


# endregion

# region Sensor


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION, kw_only=True)
class TerncySensorDescription(TerncyEntityDescription, SensorEntityDescription):
    PLATFORM: Platform = Platform.SENSOR
    value_attr: str = ""
    value_fn: Callable[[Any], StateType | date | datetime | Decimal] = lambda x: x


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION, kw_only=True)
class TemperatureDescription(TerncySensorDescription):
    key: str = "temperature"
    sub_key: str = "temperature"
    device_class: SensorDeviceClass = SensorDeviceClass.TEMPERATURE
    native_unit_of_measurement: UnitOfTemperature = UnitOfTemperature.CELSIUS
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    suggested_display_precision: int = 1
    value_attr: str = "temperature"
    value_fn: Callable[[Any], StateType | date | datetime | Decimal] = (
        lambda data: data / 10.0
    )
    old_unique_id_suffix: str = "_temptemp"


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION, kw_only=True)
class HumidityDescription(TerncySensorDescription):
    key: str = "humidity"
    sub_key: str = "humidity"
    device_class: SensorDeviceClass = SensorDeviceClass.HUMIDITY
    native_unit_of_measurement: str = PERCENTAGE
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    suggested_display_precision: int = 0
    value_attr: str = "humidity"
    old_unique_id_suffix: str = "_himidityhumidity"


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION, kw_only=True)
class IlluminanceDescription(TerncySensorDescription):
    key: str = "illuminance"
    sub_key: str = "illuminance"
    device_class: SensorDeviceClass = SensorDeviceClass.ILLUMINANCE
    native_unit_of_measurement: str = LIGHT_LUX
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    suggested_display_precision: int = 0
    value_attr: str = "luminance"
    old_unique_id_suffix: str = "_illu-illumin"


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION, kw_only=True)
class BatteryDescription(TerncySensorDescription):
    key: str = "battery"
    sub_key: str = "battery"
    entity_category: EntityCategory = EntityCategory.DIAGNOSTIC
    device_class: SensorDeviceClass = SensorDeviceClass.BATTERY
    native_unit_of_measurement: str = PERCENTAGE
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    suggested_display_precision: int = 0
    value_attr: str = "battery"


# endregion

# region Switch


@dataclass(frozen=FROZEN_ENTITY_DESCRIPTION, kw_only=True)
class TerncySwitchDescription(TerncyEntityDescription, SwitchEntityDescription):
    PLATFORM: Platform = Platform.SWITCH
    value_attr: str = "on"
    invert_state: bool = False


# endregion
