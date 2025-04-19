"""Light platform support for Terncy."""

import logging
import math

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import color as color_util

from .hass.entity import TerncyEntity
from .hass.entity_descriptions import TerncyLightDescription
from .types import AttrValue
from .utils import get_attr_value

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    TerncyEntity.ADD[f"{entry.entry_id}.light"] = async_add_entities


class TerncyLight(TerncyEntity, LightEntity):
    """Represents a Terncy light."""

    entity_description: TerncyLightDescription

    _attr_brightness: int | None = None
    _attr_color_mode: ColorMode | str | None
    _attr_color_temp_kelvin: int | None = None
    _attr_min_color_temp_kelvin = 2500
    _attr_max_color_temp_kelvin = 6500
    _attr_hs_color: tuple[float, float] | None = None
    _attr_supported_color_modes: set[ColorMode] | set[str] | None
    _attr_supported_features: LightEntityFeature

    def __init__(
        self,
        gateway,
        eid: str,
        description: TerncyLightDescription,
        init_states: list[AttrValue],
    ):
        super().__init__(gateway, eid, description, init_states)
        self._attr_color_mode = description.color_mode
        self._attr_supported_color_modes = description.supported_color_modes
        self._attr_supported_features = description.supported_features
        if ColorMode.HS in self.supported_color_modes:
            self._attr_hs_color = (0.0, 0.0)

    def update_state(self, attrs):
        # _LOGGER.debug("%s <= %s", self.eid, attrs)
        if (on_off := get_attr_value(attrs, "on")) is not None:
            self._attr_is_on = on_off == 1
        bri = get_attr_value(attrs, "brightness")
        if bri:
            self._attr_brightness = int(bri / 100 * 255)
        if color_temp_mired := get_attr_value(attrs, "colorTemperature"):
            self._attr_color_temp_kelvin = color_util.color_temperature_mired_to_kelvin(color_temp_mired)
            self._attr_color_mode = ColorMode.COLOR_TEMP
        hue = get_attr_value(attrs, "hue")
        sat = get_attr_value(attrs, "saturation")
        if hue is not None or sat is not None:
            hue = int(hue / 255 * 360.0) if hue is not None else self._attr_hs_color[0] if hasattr(self, "_attr_hs_color") else 0.0
            sat = int(sat / 255 * 100) if sat is not None else self._attr_hs_color[1] if hasattr(self, "_attr_hs_color") else 0.0
            self._attr_hs_color = (hue, sat)
            self._attr_color_mode = ColorMode.HS
        if self.hass:
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("%s async_turn_on %s", self.eid, kwargs)

        attrs = [{"attr": "on", "value": 1}]
        self._attr_is_on = True

        if ATTR_BRIGHTNESS in kwargs:
            bri = kwargs.get(ATTR_BRIGHTNESS)
            terncy_bri = math.ceil(bri / 255 * 100)
            attrs.append({"attr": "brightness", "value": terncy_bri})
            self._attr_brightness = bri

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)
            if color_temp_kelvin < self._attr_min_color_temp_kelvin:
                color_temp_kelvin = self._attr_min_color_temp_kelvin
            elif color_temp_kelvin > self._attr_max_color_temp_kelvin:
                color_temp_kelvin = self._attr_max_color_temp_kelvin
            color_temp_mired = color_util.color_temperature_kelvin_to_mired(color_temp_kelvin)
            attrs.append({"attr": "colorTemperature", "value": color_temp_mired})
            self._attr_color_temp_kelvin = color_temp_kelvin
            self._attr_color_mode = ColorMode.COLOR_TEMP

        if ATTR_HS_COLOR in kwargs:
            hs_color = kwargs.get(ATTR_HS_COLOR)
            terncy_hue = int(hs_color[0] / 360 * 255)
            terncy_sat = int(hs_color[1] / 100 * 255)
            attrs.append({"attr": "hue", "value": terncy_hue})
            attrs.append({"attr": "saturation", "value": terncy_sat})
            self._attr_hs_color = hs_color
            self._attr_color_mode = ColorMode.HS

        await self.api.set_attributes(self.eid, attrs)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("%s async_turn_off %s", self.eid, kwargs)
        self._attr_is_on = False
        await self.api.set_attribute(self.eid, "on", 0)
        self.async_write_ha_state()


TerncyEntity.NEW["light"] = TerncyLight
