"""Light platform support for Terncy."""
import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    ColorMode,  # >=2022.5
    LightEntity,
    LightEntityDescription,
    LightEntityFeature,  # >=2022.5
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
class TerncyLightDescription(TerncyEntityDescription, LightEntityDescription):
    key: str = "light"
    PLATFORM: Platform = Platform.LIGHT
    has_entity_name: bool = True
    name: str | UndefinedType | None = None
    color_mode: ColorMode | None = None
    supported_color_modes: set[ColorMode] | None = None
    supported_features: LightEntityFeature = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    def new_entity(gateway, device, description: TerncyEntityDescription):
        return TerncyLight(gateway, device, description)

    gw: "TerncyGateway" = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(Platform.LIGHT, create_entity_setup(async_add_entities, new_entity))


class TerncyLight(TerncyEntity, LightEntity):
    """Represents a Terncy light."""

    entity_description: TerncyLightDescription

    _attr_brightness: int | None = None
    _attr_color_mode: ColorMode | str | None
    _attr_color_temp: int | None = None
    _attr_max_mireds: int = 400  # 2500 K
    _attr_min_mireds: int = 153  # 6500 K
    _attr_hs_color: tuple[float, float] | None = None
    _attr_supported_color_modes: set[ColorMode] | set[str] | None
    _attr_supported_features: LightEntityFeature

    def __init__(self, gateway, device, description: TerncyLightDescription):
        super().__init__(gateway, device, description)
        self._attr_brightness = 0
        self._attr_color_mode = description.color_mode
        self._attr_color_temp = 0
        self._attr_hs_color = (0, 0)
        self._attr_supported_color_modes = description.supported_color_modes
        self._attr_supported_features = description.supported_features

    def update_state(self, attrs):
        # _LOGGER.debug("[%s] <= %s", self.unique_id, attrs)
        if (on_off := get_attr_value(attrs, "on")) is not None:
            self._attr_is_on = on_off == 1
        bri = get_attr_value(attrs, "brightness")
        if bri:
            self._attr_brightness = int(bri / 100 * 255)
        color_temp = get_attr_value(attrs, "colorTemperature")
        if color_temp is not None:
            self._attr_color_temp = color_temp
        hue = get_attr_value(attrs, "hue")
        sat = get_attr_value(attrs, "saturation")
        if hue is not None:
            hue = hue / 255 * 360.0
            self._attr_hs_color = (hue, self._attr_hs_color[1])
        if sat is not None:
            sat = sat / 255 * 100
            self._attr_hs_color = (self._attr_hs_color[0], sat)
        if self.hass:
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("async_turn_on %s", kwargs)

        attrs = [{"attr": "on", "value": 1}]
        self._attr_is_on = True

        if ATTR_BRIGHTNESS in kwargs:
            bri = kwargs.get(ATTR_BRIGHTNESS)
            terncy_bri = math.ceil(bri / 255 * 100)
            attrs.append({"attr": "brightness", "value": terncy_bri})
            self._attr_brightness = bri

        if ATTR_COLOR_TEMP in kwargs:
            color_temp = kwargs.get(ATTR_COLOR_TEMP)
            if color_temp < 50:
                color_temp = 50
            if color_temp > 400:
                color_temp = 400
            attrs.append({"attr": "colorTemperature", "value": color_temp})
            self._attr_color_temp = color_temp

        if ATTR_HS_COLOR in kwargs:
            hs_color = kwargs.get(ATTR_HS_COLOR)
            terncy_hue = int(hs_color[0] / 360 * 255)
            terncy_sat = int(hs_color[1] / 100 * 255)
            attrs.append({"attr": "hue", "value": terncy_hue})
            attrs.append({"attr": "saturation", "value": terncy_sat})
            self._attr_hs_color = hs_color

        await self.api.set_attributes(self.serial_number, attrs)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("async_turn_off %s", kwargs)
        self._attr_is_on = False
        await self.api.set_attribute(self.serial_number, "on", 0)
        self.async_write_ha_state()
