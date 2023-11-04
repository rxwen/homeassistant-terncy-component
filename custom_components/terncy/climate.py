import logging
from dataclasses import dataclass

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
)
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, Platform, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import UndefinedType

from custom_components.terncy.const import DOMAIN, TerncyEntityDescription
from custom_components.terncy.core.entity import TerncyEntity, create_entity_setup
from custom_components.terncy.utils import get_attr_value

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TerncyClimateDescription(TerncyEntityDescription, ClimateEntityDescription):
    PLATFORM: Platform = Platform.CLIMATE
    has_entity_name: bool = True
    name: str | UndefinedType | None = None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    def new_entity(gateway, eid: str, description: TerncyEntityDescription):
        return TerncyClimate(gateway, eid, description)

    gw: "TerncyGateway" = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(Platform.CLIMATE, create_entity_setup(async_add_entities, new_entity))


K_AC_MODE = "acMode"  # 制冷：1，除湿：2，通风：4，制热：8
K_AC_FAN_SPEED = "acFanSpeed"  # 快速：1，中速：2，慢速：4
K_AC_CURRENT_TEMPERATURE = "acCurrentTemperature"  # 16~30
K_AC_TARGET_TEMPERATURE = "acTargetTemperature"  # 16~30
K_AC_RUNNING = "acRunning"  # 0 or 1


class TerncyClimate(TerncyEntity, ClimateEntity):
    _attr_fan_modes: list[str] | None = [FAN_LOW, FAN_MEDIUM, FAN_HIGH]
    _attr_hvac_modes: list[HVACMode] = [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.HEAT,
    ]
    _attr_max_temp: float = 30
    _attr_min_temp: float = 16
    _attr_precision: float = 1
    _attr_supported_features: ClimateEntityFeature = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    )
    _attr_target_temperature_step: float | None = 1
    # _attr_temperature_unit: str = UnitOfTemperature.CELSIUS
    _attr_temperature_unit: str = TEMP_CELSIUS  # <2022.11

    def update_state(self, attrs):
        # _LOGGER.debug("%s <= %s", self.eid, attrs)
        if (ac_mode := get_attr_value(attrs, K_AC_MODE)) is not None:
            if ac_mode == 1:
                self._attr_hvac_mode = HVACMode.COOL
            elif ac_mode == 2:
                self._attr_hvac_mode = HVACMode.DRY
            elif ac_mode == 4:
                self._attr_hvac_mode = HVACMode.FAN_ONLY
            elif ac_mode == 8:
                self._attr_hvac_mode = HVACMode.HEAT
            else:
                self._attr_hvac_mode = None
        if (running := get_attr_value(attrs, K_AC_RUNNING)) is not None:
            if running == 0:
                self._attr_hvac_mode = HVACMode.OFF

        if (fan_speed := get_attr_value(attrs, K_AC_FAN_SPEED)) is not None:
            if fan_speed == 1:
                self._attr_fan_mode = FAN_HIGH
            elif fan_speed == 2:
                self._attr_fan_mode = FAN_MEDIUM
            elif fan_speed == 4:
                self._attr_fan_mode = FAN_LOW
            else:
                self._attr_fan_mode = None

        if (
            current_temperature := get_attr_value(attrs, K_AC_CURRENT_TEMPERATURE)
        ) is not None:
            self._attr_current_temperature = current_temperature

        if (
            target_temperature := get_attr_value(attrs, K_AC_TARGET_TEMPERATURE)
        ) is not None:
            self._attr_target_temperature = target_temperature

        if self.hass:
            self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        _LOGGER.debug("%s async_set_temperature: %s", self.eid, kwargs)
        if ATTR_TEMPERATURE in kwargs:
            temperature = kwargs[ATTR_TEMPERATURE]
            self._attr_target_temperature = temperature
            await self.api.set_attribute(self.eid, K_AC_TARGET_TEMPERATURE, temperature)
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if fan_mode == FAN_HIGH:
            self._attr_fan_mode = fan_mode
            await self.api.set_attribute(self.eid, K_AC_FAN_SPEED, 1)
        elif fan_mode == FAN_MEDIUM:
            self._attr_fan_mode = fan_mode
            await self.api.set_attribute(self.eid, K_AC_FAN_SPEED, 2)
        elif fan_mode == FAN_LOW:
            self._attr_fan_mode = fan_mode
            await self.api.set_attribute(self.eid, K_AC_FAN_SPEED, 4)
        else:
            _LOGGER.warning("Unsupported fan_mode: %s", fan_mode)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target fan mode."""
        if hvac_mode == HVACMode.OFF:
            self._attr_hvac_mode = hvac_mode
            await self.api.set_attribute(self.eid, K_AC_RUNNING, 0)
        else:
            await self.api.set_attribute(self.eid, K_AC_RUNNING, 1)
            if hvac_mode == HVACMode.COOL:
                self._attr_hvac_mode = hvac_mode
                await self.api.set_attribute(self.eid, K_AC_MODE, 1)
            elif hvac_mode == HVACMode.DRY:
                self._attr_hvac_mode = hvac_mode
                await self.api.set_attribute(self.eid, K_AC_MODE, 2)
            elif hvac_mode == HVACMode.FAN_ONLY:
                self._attr_hvac_mode = hvac_mode
                await self.api.set_attribute(self.eid, K_AC_MODE, 4)
            elif hvac_mode == HVACMode.HEAT:
                self._attr_hvac_mode = hvac_mode
                await self.api.set_attribute(self.eid, K_AC_MODE, 8)
            else:
                _LOGGER.warning("Unsupported hvac_mode: %s", hvac_mode)
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self.api.set_attribute(self.eid, K_AC_RUNNING, 1)
