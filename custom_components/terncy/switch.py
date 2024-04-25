"""Switch platform support for Terncy."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .hass.entity import TerncyEntity
from .hass.entity_descriptions import TerncySwitchDescription
from .types import AttrValue
from .utils import get_attr_value

_LOGGER = logging.getLogger(__name__)

ATTR_ON = "on"
ATTR_PURE_INPUT = "pureInput"
ATTR_DISABLE_RELAY = "disableRelay"
ATTR_DISABLED_RELAY_STATUS = "disabledRelayStatus"

KEY_WALL_SWITCH = "wall_switch"
KEY_DISABLE_RELAY = "disable_relay"
KEY_DISABLED_RELAY_STATUS = "disabled_relay_status"


async def async_setup_entry(
    hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    TerncyEntity.ADD[f"{entry.entry_id}.switch"] = async_add_entities


class TerncyCommonSwitch(TerncyEntity, SwitchEntity):
    """Represents a Terncy Switch."""

    entity_description: TerncySwitchDescription

    def update_state(self, attrs: list[AttrValue]):
        """Update terncy state."""
        # _LOGGER.debug("%s <= %s", self.eid, attrs)
        if (
            value := get_attr_value(attrs, self.entity_description.value_attr)
        ) is not None:
            self._attr_is_on = value == self.attr_value_on
        if self.hass:
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        self._attr_is_on = True
        await self.api.set_attribute(
            self.eid,
            self.entity_description.value_attr,
            self.attr_value_on,
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._attr_is_on = False
        await self.api.set_attribute(
            self.eid,
            self.entity_description.value_attr,
            self.attr_value_off,
        )
        self.async_write_ha_state()

    @property
    def attr_value_on(self):
        return 1 if not self.entity_description.invert_state else 0

    @property
    def attr_value_off(self):
        return 0 if not self.entity_description.invert_state else 1


class TerncyWallSwitch(TerncyCommonSwitch):
    """Represents a Terncy Wall Switch"""

    _disableRelay: bool | None = None

    def update_state(self, attrs: list[AttrValue]):
        """Update terncy state."""
        # _LOGGER.debug("%s <= %s", self.eid, attrs)
        for av in attrs:
            if av["attr"] == ATTR_ON:
                self._attr_is_on = av["value"] == 1
            elif av["attr"] == ATTR_DISABLE_RELAY:
                self._disableRelay = av["value"] == 1
        if self.hass:
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        if self._disableRelay:
            return False
        return self._attr_available


class DisableRelaySwitch(TerncyCommonSwitch):
    """Need pure_input enabled"""

    _pure_input: bool | None = None

    def update_state(self, attrs: list[AttrValue]):
        """Update terncy state."""
        # _LOGGER.debug("%s <= %s", self.eid, attrs)
        for av in attrs:
            if av["attr"] == ATTR_PURE_INPUT:
                self._pure_input = av["value"] == 1
            elif av["attr"] == ATTR_DISABLE_RELAY:
                self._attr_is_on = av["value"] == 1
        if self.hass:
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        if self._pure_input:
            return self._attr_available
        else:
            return False


class DisabledRelayStatusSwitch(TerncyCommonSwitch):
    """Need pure_input and disable_relay all enabled"""

    _pure_input: bool | None = None
    _disableRelay: bool | None = None

    def update_state(self, attrs: list[AttrValue]):
        """Update terncy state."""
        # _LOGGER.debug("%s <= %s", self.eid, attrs)
        for av in attrs:
            if av["attr"] == ATTR_PURE_INPUT:
                self._pure_input = av["value"] == 1
            elif av["attr"] == ATTR_DISABLE_RELAY:
                self._disableRelay = av["value"] == 1
            elif av["attr"] == ATTR_DISABLED_RELAY_STATUS:
                self._attr_is_on = av["value"] == 1
        if self.hass:
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        if self._pure_input and self._disableRelay:
            return self._attr_available
        else:
            return False

    @property
    def icon(self) -> str | None:
        if self.is_on:
            return "mdi:electric-switch-closed"
        else:
            return "mdi:electric-switch"


TerncyEntity.NEW["switch"] = TerncyCommonSwitch
TerncyEntity.NEW[f"switch.key.{KEY_WALL_SWITCH}"] = TerncyWallSwitch
TerncyEntity.NEW[f"switch.key.{KEY_DISABLE_RELAY}"] = DisableRelaySwitch
TerncyEntity.NEW[f"switch.key.{KEY_DISABLED_RELAY_STATUS}"] = DisabledRelayStatusSwitch  # fmt: skip
