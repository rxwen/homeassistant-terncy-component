"""HA>=2023.7"""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.light import ColorMode
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import EntityCategory

from ..const import (
    ACTION_DOUBLE_PRESS,
    ACTION_LONG_PRESS,
    ACTION_ROTATION,
    ACTION_SINGLE_PRESS,
    EVENT_ENTITY_BUTTON_EVENTS,
    EVENT_ENTITY_DIAL_EVENTS,
    HAS_EVENT_PLATFORM,
    PROFILE_AC_UNIT_MACHINE,
    PROFILE_COLOR_DIMMABLE_LIGHT,
    PROFILE_COLOR_LIGHT,
    PROFILE_COLOR_TEMPERATURE_LIGHT,
    PROFILE_CURTAIN,
    PROFILE_DIMMABLE_COLOR_TEMPERATURE_LIGHT,
    PROFILE_DIMMABLE_LIGHT,
    PROFILE_DIMMABLE_LIGHT2,
    PROFILE_DOOR_SENSOR,
    PROFILE_EXTENDED_COLOR_LIGHT,
    PROFILE_EXTENDED_COLOR_LIGHT2,
    PROFILE_GAS,
    PROFILE_HA_TEMPERATURE_HUMIDITY,
    PROFILE_HA_THERMASTAT,
    PROFILE_LOCK,
    PROFILE_OCCUPANCY_SENSOR,
    PROFILE_ONOFF_LIGHT,
    PROFILE_PIR,
    PROFILE_PLUG,
    PROFILE_PRESENCE_SENSOR,
    PROFILE_SMART_DIAL,
    PROFILE_SWITCH,
    PROFILE_XY_SINGLE_AIR_COND,
    PROFILE_YAN_BUTTON,
)
from ..hass.entity_descriptions import (
    BatteryDescription,
    HumidityDescription,
    IlluminanceDescription,
    TemperatureDescription,
    TerncyBinarySensorDescription,
    TerncyClimateDescription,
    TerncyCoverDescription,
    TerncyEntityDescription,
    TerncyLightDescription,
    TerncySwitchDescription,
)
from ..switch import (
    ATTR_DISABLED_RELAY_STATUS,
    ATTR_DISABLE_RELAY,
    ATTR_ON,
    ATTR_PURE_INPUT,
    KEY_DISABLED_RELAY_STATUS,
    KEY_DISABLE_RELAY,
    KEY_WALL_SWITCH,
)

PROFILES: dict[int, list[TerncyEntityDescription]] = {
    PROFILE_PIR: [
        # TerncyButtonDescription(),
        TemperatureDescription(),
        IlluminanceDescription(),
        BatteryDescription(),
        TerncyBinarySensorDescription(
            key="motion",
            sub_key="motionl",
            device_class=BinarySensorDeviceClass.MOTION,
            translation_key="motion_left",
            value_attr="motionL",
        ),
        TerncyBinarySensorDescription(
            key="motion",
            sub_key="motionr",
            device_class=BinarySensorDeviceClass.MOTION,
            translation_key="motion_right",
            value_attr="motionR",
        ),
        TerncyBinarySensorDescription(
            key="motion",
            sub_key="motion",
            device_class=BinarySensorDeviceClass.MOTION,
            entity_registry_enabled_default=False,
            value_attr="motion",
        ),
    ],
    PROFILE_PLUG: [
        TerncySwitchDescription(
            key="switch",
            device_class=SwitchDeviceClass.OUTLET,
            name=None,
            value_attr=ATTR_ON,
        ),
    ],
    PROFILE_ONOFF_LIGHT: [
        TerncySwitchDescription(
            key=KEY_WALL_SWITCH,
            device_class=SwitchDeviceClass.SWITCH,
            name=None,
            value_attr=ATTR_ON,
        ),
        # TerncyButtonDescription(),
        TerncySwitchDescription(
            key="switch",
            sub_key="pure_input",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:remote",
            translation_key="pure_input",
            value_attr=ATTR_PURE_INPUT,
        ),
        TerncySwitchDescription(
            key=KEY_DISABLE_RELAY,
            sub_key="disable_relay",
            entity_category=EntityCategory.CONFIG,
            translation_key="disable_relay",
            value_attr=ATTR_DISABLE_RELAY,
        ),
        TerncySwitchDescription(
            key=KEY_DISABLED_RELAY_STATUS,
            sub_key="disabled_relay_status",
            entity_category=EntityCategory.CONFIG,
            translation_key="disabled_relay_status",
            value_attr=ATTR_DISABLED_RELAY_STATUS,
        ),
    ],
    PROFILE_DOOR_SENSOR: [
        TerncyBinarySensorDescription(
            key="contact",
            name=None,
            value_attr="contact",
        ),
        TemperatureDescription(),
        BatteryDescription(),
    ],
    PROFILE_SWITCH: [
        TerncySwitchDescription(
            key="switch",
            device_class=SwitchDeviceClass.SWITCH,
            name=None,
            value_attr=ATTR_ON,
        ),
        # TerncyButtonDescription(),
    ],
    PROFILE_CURTAIN: [
        TerncyCoverDescription(
            key="cover",
            device_class=CoverDeviceClass.CURTAIN,
        ),
    ],
    PROFILE_YAN_BUTTON: [
        # TerncyButtonDescription(),
    ],
    PROFILE_SMART_DIAL: [
        # TerncyButtonDescription(
        #     event_types=[*EVENT_ENTITY_BUTTON_EVENTS, "rotation"],
        # ),
        BatteryDescription(),
    ],
    PROFILE_COLOR_LIGHT: [
        TerncyLightDescription(
            color_mode=ColorMode.HS,
            supported_color_modes={ColorMode.HS},
        ),
    ],
    PROFILE_AC_UNIT_MACHINE: [
        TerncyClimateDescription(
            key="climate",
        ),
    ],
    PROFILE_HA_THERMASTAT: [
        TerncyClimateDescription(
            key="climate",
        ),
    ],
    PROFILE_XY_SINGLE_AIR_COND: [
        TerncyClimateDescription(
            key="climate",
        ),
    ],
    PROFILE_LOCK: [
        TerncyBinarySensorDescription(
            key="lock",
            device_class=BinarySensorDeviceClass.LOCK,
            name=None,
            value_attr="lockState",
            value_map={1: False, 2: True},
        ),
        BatteryDescription(),
    ],
    PROFILE_EXTENDED_COLOR_LIGHT: [
        TerncyLightDescription(
            color_mode=ColorMode.HS,
            supported_color_modes={ColorMode.COLOR_TEMP, ColorMode.HS},
        ),
    ],
    PROFILE_COLOR_TEMPERATURE_LIGHT: [
        TerncyLightDescription(
            color_mode=ColorMode.COLOR_TEMP,
            supported_color_modes={ColorMode.COLOR_TEMP},
        ),
    ],
    PROFILE_HA_TEMPERATURE_HUMIDITY: [
        TemperatureDescription(),
        HumidityDescription(),
        BatteryDescription(),
    ],
    PROFILE_DIMMABLE_COLOR_TEMPERATURE_LIGHT: [
        TerncyLightDescription(
            color_mode=ColorMode.COLOR_TEMP,
            supported_color_modes={ColorMode.COLOR_TEMP},
        ),
    ],
    PROFILE_OCCUPANCY_SENSOR: [
        TerncyBinarySensorDescription(
            key="motion",
            sub_key="motion",
            device_class=BinarySensorDeviceClass.MOTION,
            value_attr="motion",
        ),
        BatteryDescription(
            required_attrs=["battery"],
        ),
        TerncyBinarySensorDescription(
            key="motion",
            sub_key="motionl",
            device_class=BinarySensorDeviceClass.MOTION,
            translation_key="motion_left",
            value_attr="motionL",
            required_attrs=["motionL"],
        ),
        TerncyBinarySensorDescription(
            key="motion",
            sub_key="motionr",
            device_class=BinarySensorDeviceClass.MOTION,
            translation_key="motion_right",
            value_attr="motionR",
            required_attrs=["motionR"],
        ),
    ],
    PROFILE_DIMMABLE_LIGHT: [
        TerncyLightDescription(
            color_mode=ColorMode.BRIGHTNESS,
            supported_color_modes={ColorMode.BRIGHTNESS},
        ),
    ],
    PROFILE_DIMMABLE_LIGHT2: [
        TerncyLightDescription(
            color_mode=ColorMode.BRIGHTNESS,
            supported_color_modes={ColorMode.BRIGHTNESS},
        ),
    ],
    PROFILE_GAS: [
        TerncyBinarySensorDescription(
            key="gas",
            sub_key="gas",
            device_class=BinarySensorDeviceClass.GAS,
            name=None,
            value_attr="iasZoneStatus",
            value_map={32: False, 33: True},
        ),
    ],
    PROFILE_COLOR_DIMMABLE_LIGHT: [
        TerncyLightDescription(
            color_mode=ColorMode.HS,
            supported_color_modes={ColorMode.COLOR_TEMP, ColorMode.HS},
        ),
    ],
    PROFILE_EXTENDED_COLOR_LIGHT2: [
        TerncyLightDescription(
            color_mode=ColorMode.HS,
            supported_color_modes={ColorMode.COLOR_TEMP, ColorMode.HS},
        ),
    ],
    PROFILE_PRESENCE_SENSOR: [
        TerncyBinarySensorDescription(
            key="presenceStatus",
            device_class=BinarySensorDeviceClass.PRESENCE,
            value_attr="presenceStatus",
        ),
    ],
}

if HAS_EVENT_PLATFORM:
    from ..hass.entity_descriptions import TerncyButtonDescription

    EVENT_ENTITY_EVENTS_MAP = {
        PROFILE_PIR: EVENT_ENTITY_BUTTON_EVENTS,
        PROFILE_ONOFF_LIGHT: EVENT_ENTITY_BUTTON_EVENTS,
        PROFILE_SWITCH: EVENT_ENTITY_BUTTON_EVENTS,
        PROFILE_YAN_BUTTON: EVENT_ENTITY_BUTTON_EVENTS,
        PROFILE_SMART_DIAL: EVENT_ENTITY_DIAL_EVENTS,
    }

    SINGLE = TerncyButtonDescription(
        key=ACTION_SINGLE_PRESS,
        sub_key=ACTION_SINGLE_PRESS,
        translation_key=ACTION_SINGLE_PRESS,
        event_types=[ACTION_SINGLE_PRESS],
    )
    DOUBLE = TerncyButtonDescription(
        key=ACTION_DOUBLE_PRESS,
        sub_key=ACTION_DOUBLE_PRESS,
        translation_key=ACTION_DOUBLE_PRESS,
        event_types=[ACTION_DOUBLE_PRESS],
        entity_registry_enabled_default=False,  # 双击默认禁用
    )
    LONG = TerncyButtonDescription(
        key=ACTION_LONG_PRESS,
        sub_key=ACTION_LONG_PRESS,
        translation_key=ACTION_LONG_PRESS,
        event_types=[ACTION_LONG_PRESS],
        entity_registry_enabled_default=False,  # 长按默认禁用
    )
    ROTATE = TerncyButtonDescription(
        key=ACTION_ROTATION,
        sub_key=ACTION_ROTATION,
        translation_key=ACTION_ROTATION,
        event_types=[ACTION_ROTATION],
        entity_registry_enabled_default=False,  # 旋转默认禁用
    )
    extra_descriptions = [SINGLE, DOUBLE, LONG]

    for profile in EVENT_ENTITY_EVENTS_MAP:
        event_types = list(EVENT_ENTITY_EVENTS_MAP.get(profile))
        button_desc = TerncyButtonDescription(
            event_types=event_types,
            entity_registry_enabled_default=False,  # 旧版的通用按钮实体默认禁用
        )
        descriptions = PROFILES.get(profile)
        descriptions.append(button_desc)
        # 为最常用的 单击、双击、长按 再单独创建一个 event 实体
        descriptions.extend(extra_descriptions)
        # 支持旋转的话就再加个旋转
        if ACTION_ROTATION in event_types:
            descriptions.append(ROTATE)
