"""Smart plug platform support for Terncy."""
import logging
from homeassistant.helpers import device_registry as dr

from homeassistant.components.switch import (
    DEVICE_CLASS_OUTLET,
    DEVICE_CLASS_SWITCH,
    DEVICE_CLASSES,
    SwitchEntity,
)
from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
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
    ACTION_TRIPLE_PRESS,
    ACTION_LONG_PRESS,
)
from .utils import get_attr_value

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Old way of setting up Terncy smart plugs.

    Can only be called when a user accidentally mentions Terncy platform in their
    config. But even in that case it would have been ignored.
    """
    _LOGGER.info(" terncy smart plug async_setup_platform")


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Terncy smart plugs from a config entry."""
    _LOGGER.info("setup terncy smart plug platform")


class TerncySmartPlug(SwitchEntity):
    """Representation of a Terncy smart plug."""

    def __init__(self, api, devid, name, model, version, features):
        """Initialize the smart plug."""
        self._device_id = devid
        self.hub_id = api.dev_id
        self._name = name
        self.model = model
        self.version = version
        self.api = api
        self.is_available = False
        self._features = features
        self._onoff = False

    def update_state(self, attrs):
        """Updateterncy state."""
        _LOGGER.info("update state event to %s", attrs)
        on_off = get_attr_value(attrs, "on")
        if on_off is not None:
            self._onoff = on_off == 1

    @property
    def unique_id(self):
        """Return terncy unique id."""
        return self._device_id

    @property
    def device_id(self):
        """Return terncy device id."""
        return self._device_id

    @property
    def device_class(self):
        """Return if terncy device is available."""
        return DEVICE_CLASS_OUTLET

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
    def supported_features(self):
        """Return the terncy device feature."""
        return self._features

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

    async def async_turn_on(self, **kwargs):
        """Turn on terncy smart plug."""
        _LOGGER.info("turn on %s", kwargs)
        self._onoff = True
        await self.api.set_onoff(self._device_id, 1)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn off terncy smart plug."""
        _LOGGER.info("turn off")
        self._onoff = False
        await self.api.set_onoff(self._device_id, 0)
        self.async_write_ha_state()


class TerncySwitch(SwitchEntity):
    """Representation of a Terncy Switch."""

    def __init__(self, api, devid, name, model, version, features):
        """Initialize the switch."""
        self._device_id = devid
        self.hub_id = api.dev_id
        self._name = name
        self.model = model
        self.version = version
        self.api = api
        self.is_available = False
        self._features = features
        self._onoff = False

    def update_state(self, attrs):
        """Updateterncy state."""
        _LOGGER.info("update state event to %s", attrs)
        on_off = get_attr_value(attrs, "on")
        if on_off is not None:
            self._onoff = on_off == 1

    @property
    def unique_id(self):
        """Return terncy unique id."""
        return self._device_id

    @property
    def device_id(self):
        """Return terncy device id."""
        return self._device_id

    @property
    def device_class(self):
        """Return if terncy device is available."""
        return DEVICE_CLASS_SWITCH

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
    def supported_features(self):
        """Return the terncy device feature."""
        return self._features

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

    async def async_turn_on(self, **kwargs):
        """Turn on terncy smart plug."""
        _LOGGER.info("turn on %s", kwargs)
        self._onoff = True
        await self.api.set_onoff(self._device_id, 1)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn off terncy smart plug."""
        _LOGGER.info("turn off")
        self._onoff = False
        await self.api.set_onoff(self._device_id, 0)
        self.async_write_ha_state()

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
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: ACTION_TRIPLE_PRESS,
            },
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: ACTION_LONG_PRESS,
            },
        ]

class TerncyScene(SwitchEntity):
    """Representation of a Terncy scene."""

    def __init__(self, api, devid, name, model, version, features):
        """Initialize the scene."""
        self._device_id = devid
        self.hub_id = api.dev_id
        self._name = name
        self.model = model
        self.version = version
        self.api = api
        self.is_available = False
        self._features = features
        self._onoff = False

    def update_state(self, attrs):
        """Updateterncy state."""
        _LOGGER.info("update state event to %s", attrs)
        on_off = get_attr_value(attrs, "on")
        if on_off is not None:
            self._onoff = on_off == 1

    @property
    def unique_id(self):
        """Return terncy unique id."""
        return self._device_id

    @property
    def device_id(self):
        """Return terncy device id."""
        return self._device_id

    @property
    def device_class(self):
        """Return if terncy device is available."""
        return DEVICE_CLASS_OUTLET

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
    def supported_features(self):
        """Return the terncy device feature."""
        return self._features

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

    async def async_turn_on(self, **kwargs):
        """Turn on terncy smart plug."""
        _LOGGER.info("turn on %s", kwargs)
        self._onoff = True
        await self.api.set_onoff(self._device_id, 1)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn off terncy smart plug."""
        _LOGGER.info("turn off")
        self._onoff = False
        await self.api.set_onoff(self._device_id, 0)
        self.async_write_ha_state()

class TerncyButton(ButtonEntity):
    """Representation of a Terncy Stateless Button."""

    _attr_device_class = ButtonDeviceClass.RESTART

    def __init__(self, api, devid, name, model, version, features):
        """Initialize the button."""
        _LOGGER.info("create terncybutton AAA slkdjfslkdfj")
        self._device_id = devid
        self.hub_id = api.dev_id
        self._name = name
        self.model = model
        self.version = version
        self.api = api
        self.is_available = False
        self._features = features
        self._onoff = False

    def update_state(self, attrs):
        """Updateterncy state."""
        _LOGGER.info("update state event to %s", attrs)
        on_off = get_attr_value(attrs, "on")
        if on_off is not None:
            self._onoff = on_off == 1

    @property
    def unique_id(self):
        """Return terncy unique id."""
        return self._device_id

    @property
    def device_id(self):
        """Return terncy device id."""
        return self._device_id

    @property
    def device_class(self):
        return ButtonDeviceClass.UPDATE.value

    @property
    def name(self):
        """Return terncy device name."""
        return self._name

    @property
    def available(self):
        """Return if terncy device is available."""
        return self.is_available

    @property
    def supported_features(self):
        """Return the terncy device feature."""
        return self._features

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
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: ACTION_TRIPLE_PRESS,
            },
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: ACTION_LONG_PRESS,
            },
        ]

    async def async_turn_on(self, **kwargs):
        """Turn on terncy button."""
        _LOGGER.info("no need to turn on")

    async def async_turn_off(self, **kwargs):
        """Turn off terncy button."""
        _LOGGER.info("no need to turn off")

    async def async_press(self) -> None:
        _LOGGER.info(" terncy button pressed, nothing to do")
