import logging
from typing import Any

from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_PLATFORM,
    CONF_TYPE,
)

from .entity import TerncyEntity
from ..const import DEVICE_TRIGGER_ACTIONS_MAP, DOMAIN, HAS_EVENT_PLATFORM
from ..types import AttrValue

_LOGGER = logging.getLogger(__name__)


class TerncyDevice:
    """对应的是HA里的一个Device，也对应Terncy那边一个profile。
    代表一个功能，比如一个四键开关就会有4个TerncyDevice
    """

    def __init__(self, device_serial: str, serial_number: str, profile: int):
        """
        device_serial (str): entityAvailable、entityDeleted、offline 事件查找设备用
        serial_number (str): device trigger 查找设备用
        profile (int): device trigger 查找 actions 用
        """

        self.device_serial = device_serial  # -00 结尾的
        self.serial_number = serial_number  # -01 -02 ... 结尾的
        self.profile = profile
        self.entities: list[TerncyEntity] = []

        self.identifiers = {(DOMAIN, serial_number)}

    def set_available(self, available: bool):
        """设备是否可用"""
        for entity in self.entities:
            entity.set_available(available)

    def update_state(self, attributes: list[AttrValue]):
        for entity in self.entities:
            entity.update_state(attributes)

    def get_triggers(self, device_id: str) -> list[dict[str, str]]:
        if actions := DEVICE_TRIGGER_ACTIONS_MAP.get(self.profile):
            base = {
                CONF_PLATFORM: "device",
                CONF_DOMAIN: DOMAIN,
                CONF_DEVICE_ID: device_id,
                "metadata": {"secondary": False},
            }
            return [{**base, CONF_TYPE: action} for action in actions]
        else:
            return []

    def trigger_event(
        self, event_type: str, event_attributes: dict[str, Any] | None = None
    ):
        if HAS_EVENT_PLATFORM:
            from ..event import TerncyEvent

            for entity in self.entities:
                if isinstance(entity, TerncyEvent):
                    entity.trigger_event(event_type, event_attributes)
