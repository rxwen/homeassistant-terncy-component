"""Provides device triggers for Terncy."""
import logging
_LOGGER = logging.getLogger(__name__)
from typing import List

import voluptuous as vol
from homeassistant.components.automation import AutomationActionType
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.device_automation.exceptions import (
    InvalidDeviceAutomationConfig,
)
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_EVENT,
    CONF_PLATFORM,
    CONF_TYPE,
    CONF_FOR,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    EVENT_DATA_SOURCE,
    ACTION_SINGLE_PRESS,
    ACTION_DOUBLE_PRESS,
    ACTION_TRIPLE_PRESS,
    ACTION_LONG_PRESS,
)

SUPPORTED_INPUTS_EVENTS_TYPES = [ACTION_SINGLE_PRESS, ACTION_DOUBLE_PRESS, ACTION_TRIPLE_PRESS, ACTION_LONG_PRESS]

TERNCY_BUTTON_TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(SUPPORTED_INPUTS_EVENTS_TYPES),
        vol.Optional(CONF_ENTITY_ID): cv.entity_id,
        # vol.Optional(CONF_FOR): cv.positive_time_period_dict,
    }
)

TRIGGER_SCHEMA = vol.Any(
    TERNCY_BUTTON_TRIGGER_SCHEMA,
)


async def async_validate_trigger_config(hass: HomeAssistant, config: ConfigType):
    """Validate config."""

    schema = TERNCY_BUTTON_TRIGGER_SCHEMA

    return schema(config)


from homeassistant.helpers import (
    entity_registry,
)

async def async_get_triggers(hass: HomeAssistant, device_id: str) -> List[dict]:
    """List device triggers for Terncy devices."""
    triggers = []
    device_registry = await hass.helpers.device_registry.async_get_registry()
    device = device_registry.async_get(device_id)
    devid = min(device.identifiers)[1]
    for tern in hass.data[DOMAIN].values():
        if devid in tern.hass_platform_data.parsed_devices:
            triggers.extend(tern.hass_platform_data.parsed_devices[devid].get_trigger(device.id))
            break

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: AutomationActionType,
    automation_info: dict,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    device_id = config[CONF_DEVICE_ID]
    device_registry = await hass.helpers.device_registry.async_get_registry()
    device = device_registry.async_get(device_id)
    _LOGGER.info(device.identifiers)
    devid = min(device.identifiers)[1]
    _LOGGER.info("async_attach_trigger for %s" % devid)
    schema = TERNCY_BUTTON_TRIGGER_SCHEMA
    config = schema(config)
    event_config = {
        event_trigger.CONF_PLATFORM: CONF_EVENT,
        event_trigger.CONF_EVENT_TYPE: config[CONF_TYPE],
        event_trigger.CONF_EVENT_DATA: {
            EVENT_DATA_SOURCE: devid,
        },
    }
    event_config = event_trigger.TRIGGER_SCHEMA(event_config)
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, automation_info, platform_type="device"
    )

async def async_get_trigger_capabilities(hass: HomeAssistant, config: dict) -> dict:
    """List trigger capabilities."""
    return {}

