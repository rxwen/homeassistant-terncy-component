"""Curtain platform support for Terncy."""
import logging
from homeassistant.helpers import device_registry as dr

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_SAFETY,
    DEVICE_CLASS_OPENING,
    DEVICE_CLASSES,
    BinarySensorEntity,
)
from homeassistant.components.sensor import (
    DEVICE_CLASS_TEMPERATURE,
)
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_ENTITY_ID,
    CONF_DOMAIN,
    CONF_EVENT,
    CONF_PLATFORM,
    CONF_TYPE,
)

from .const import (
    DOMAIN,
    TERNCY_MANU_NAME,
    ACTION_SINGLE_PRESS,
    ACTION_DOUBLE_PRESS,
    ACTION_LONG_PRESS,
)

from .utils import get_attr_value

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Old way of setting up Terncy curtain.

    Can only be called when a user accidentally mentions Terncy platform in their
    config. But even in that case it would have been ignored.
    """
    _LOGGER.info(" terncy curtain async_setup_platform")


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Terncy curtain from a config entry."""
    _LOGGER.info("setup terncy curtain platform")


class TerncyDoorSensor(BinarySensorEntity):
    """Representation of a Terncy door sensor."""

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
        self._on = 0

    def update_state(self, attrs):
        """Updateterncy state."""
        _LOGGER.info("update state event to %s", attrs)
        on = get_attr_value(attrs, "contact")
        if on is not None:
            self._on = on

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
        return self._on == 1

    @property
    def available(self):
        """Return if terncy device is available."""
        return self.is_available

    @property
    def device_class(self):
        """Return if terncy device is available."""
        return DEVICE_CLASS_OPENING

    @property
    def supported_features(self):
        """Return the terncy device feature."""
        return 0

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

    @property
    def device_state_attributes(self):
        """Get terncy curtain states."""
        return {}


class TerncyMotionSensor(BinarySensorEntity):
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
        self._on = 0

    def update_state(self, attrs):
        """Updateterncy state."""
        _LOGGER.info("update state event to %s", attrs)
        on = get_attr_value(attrs, "motion")
        if on is not None:
            self._on = on

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
        return self._on == 1

    @property
    def available(self):
        """Return if terncy device is available."""
        return self.is_available

    @property
    def device_class(self):
        """Return if terncy device is available."""
        return DEVICE_CLASS_MOTION

    @property
    def supported_features(self):
        """Return the terncy device feature."""
        return 0

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

    @property
    def device_state_attributes(self):
        """Get terncy curtain states."""
        return {}

    def get_trigger(self, id):
        return [
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: ACTION_SINGLE_PRESS,
            },
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: ACTION_DOUBLE_PRESS,
            },
        ]
