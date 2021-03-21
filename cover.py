"""Curtain platform support for Terncy."""
import logging
from homeassistant.helpers import device_registry as dr

from homeassistant.components.cover import (
    DEVICE_CLASS_BLIND,
    DEVICE_CLASSES,
    ATTR_POSITION,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    CoverEntity,
)

from .const import DOMAIN, TERNCY_MANU_NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Old way of setting up Terncy curtain.

    Can only be called when a user accidentally mentions Terncy platform in their
    config. But even in that case it would have been ignored.
    """
    _LOGGER.info(" terncy curtain async_setup_platform")


def get_attr_value(attrs, key):
    """Read attr value from terncy attributes."""
    for att in attrs:
        if "attr" in att and att["attr"] == key:
            return att["value"]
    return None


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Terncy curtain from a config entry."""
    _LOGGER.info("setup terncy curtain platform")


class TerncyCurtain(CoverEntity):
    """Representation of a Terncy curtain."""

    def __init__(self, api, devid, name, model, version, features):
        """Initialize the curtain."""
        self._device_id = devid
        self.hub_id = api.dev_id
        self._name = name
        self.model = model
        self.version = version
        self.api = api
        self.is_available = False
        self._features = features
        self._percent = 0

    def update_state(self, attrs):
        """Updateterncy state."""
        _LOGGER.info("update state event to %s", attrs)
        percent = get_attr_value(attrs, "curtainPercent")
        if percent is not None:
            self._percent = percent

    @property
    def unique_id(self):
        """Return terncy unique id."""
        return self._device_id

    @property
    def device_id(self):
        """Return terncy device id."""
        return self._device_id

    @property
    def name(self):
        """Return terncy device name."""
        return self._name

    @property
    def is_on(self):
        """Return if terncy device is on."""
        return self._onoff

    @property
    def available(self):
        """Return if terncy device is available."""
        return self.is_available

    @property
    def device_class(self):
        """Return if terncy device is available."""
        return DEVICE_CLASS_BLIND

    @property
    def supported_features(self):
        """Return the terncy device feature."""
        return SUPPORT_SET_POSITION | SUPPORT_OPEN | SUPPORT_CLOSE

    @property
    def current_cover_position(self):
        """Return if terncy device is available."""
        return self._percent

    @property
    def is_closed(self):
        """Return if terncy device is available."""
        return self._percent == 0

    @property
    def is_opening(self):
        """Return if terncy device is available."""
        return False

    @property
    def is_closing(self):
        """Return if terncy device is available."""
        return False

    @property
    def current_cover_tilt_position(self):
        """Return if terncy device is available."""
        return None

    @property
    def device_info(self):
        """Return the terncy device info."""
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "connections": {(dr.CONNECTION_ZIGBEE, self.device_id)},
            "name": self.name,
            "manufacturer": TERNCY_MANU_NAME,
            "model": self.model,
            "sw_version": self.version,
            "via_device": (DOMAIN, self.hub_id),
        }

    async def async_close_cover(self, **kwargs):
        """Turn on terncy curtain."""
        _LOGGER.info("close cover %s", kwargs)
        await self.api.set_attribute(self._device_id, "curtainPercent", 0, 0)
        self.async_write_ha_state()

    async def async_open_cover(self, **kwargs):
        """Turn on terncy curtain."""
        _LOGGER.info("close cover %s", kwargs)
        await self.api.set_attribute(self._device_id, "curtainPercent", 100, 0)
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs):
        """Turn on terncy curtain."""
        _LOGGER.info("set cover position %s", kwargs)
        percent = kwargs[ATTR_POSITION]
        await self.api.set_attribute(self._device_id, "curtainPercent", percent, 0)
        self.async_write_ha_state()

    @property
    def device_state_attributes(self):
        """Get terncy curtain states."""
        return {}
