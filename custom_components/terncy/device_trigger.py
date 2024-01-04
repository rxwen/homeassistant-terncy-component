"""Provides device triggers for Terncy."""
import logging

import voluptuous as vol
from homeassistant.components.automation import TriggerActionType
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_ENTITY_ID, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.typing import ConfigType

from .const import (
    ACTION_DOUBLE_PRESS,
    ACTION_LONG_PRESS,
    ACTION_PRESSED,
    ACTION_ROTATION,
    ACTION_SINGLE_PRESS,
    ACTION_TRIPLE_PRESS,
    DOMAIN,
    EVENT_DATA_CLICK_TIMES,
    EVENT_DATA_SOURCE,
)

_LOGGER = logging.getLogger(__name__)

TERNCY_BUTTON_TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(
            [
                ACTION_LONG_PRESS,
                ACTION_ROTATION,
                ACTION_SINGLE_PRESS,
                ACTION_DOUBLE_PRESS,
                ACTION_TRIPLE_PRESS,
            ]
        ),
        vol.Optional(EVENT_DATA_CLICK_TIMES): cv.positive_int,
        vol.Optional(CONF_ENTITY_ID): cv.entity_id_or_uuid,  # remove?
        # vol.Optional(CONF_FOR): cv.positive_time_period_dict,
    }
)

TRIGGER_SCHEMA = vol.Any(
    TERNCY_BUTTON_TRIGGER_SCHEMA,
)


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> list[dict]:
    """这里是返回给UI的列表用的，当用户选择某一项触发条件的时候，会用这里返回的数据填充配置。"""
    device_registry = dr.async_get(hass)
    device_entry: DeviceEntry = device_registry.async_get(device_id)

    triggers: list[dict[str, str]] = []

    # Determine which triggers are supported by this device_id ...
    eid = min(device_entry.identifiers)[1]
    _LOGGER.debug("async_get_triggers %s %s", device_id, eid)
    for gateway in hass.data[DOMAIN].values():
        for device in gateway.parsed_devices.values():
            if eid == device.eid:
                triggers.extend(device.get_triggers(device_id))

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: dict,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    _LOGGER.debug("async_attach_trigger %s", config)
    device_id: str = config[CONF_DEVICE_ID]
    device_registry = dr.async_get(hass)
    device_entry: DeviceEntry = device_registry.async_get(device_id)
    eid = min(device_entry.identifiers)[1]

    event_data = {
        CONF_DEVICE_ID: device_id,
        EVENT_DATA_SOURCE: eid,
    }

    if config[CONF_TYPE] == ACTION_LONG_PRESS:
        event_type = f"{DOMAIN}_{ACTION_LONG_PRESS}"
    elif config[CONF_TYPE] == ACTION_SINGLE_PRESS:
        event_type = f"{DOMAIN}_{ACTION_PRESSED}"
        event_data[EVENT_DATA_CLICK_TIMES] = config.get(EVENT_DATA_CLICK_TIMES, 1)
    elif config[CONF_TYPE] == ACTION_DOUBLE_PRESS:
        event_type = f"{DOMAIN}_{ACTION_PRESSED}"
        event_data[EVENT_DATA_CLICK_TIMES] = 2
    elif config[CONF_TYPE] == ACTION_TRIPLE_PRESS:
        event_type = f"{DOMAIN}_{ACTION_PRESSED}"
        event_data[EVENT_DATA_CLICK_TIMES] = 3
    elif config[CONF_TYPE] == ACTION_ROTATION:
        event_type = f"{DOMAIN}_{ACTION_ROTATION}"
    else:
        # maybe never here
        event_type = f"{DOMAIN}_{config[CONF_TYPE]}"
        if EVENT_DATA_CLICK_TIMES in config:
            event_data[EVENT_DATA_CLICK_TIMES] = config[EVENT_DATA_CLICK_TIMES]

    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: event_type,
            event_trigger.CONF_EVENT_DATA: event_data,
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )


async def async_get_trigger_capabilities(hass: HomeAssistant, config: dict) -> dict:
    """List trigger capabilities."""
    _LOGGER.debug("async_get_trigger_capabilities %s", config)

    if config[CONF_TYPE] == ACTION_SINGLE_PRESS:
        return {
            "extra_fields": vol.Schema(
                {
                    vol.Optional(EVENT_DATA_CLICK_TIMES): vol.All(
                        vol.Coerce(int), vol.Range(min=1)
                    ),
                }
            )
        }

    return {}
