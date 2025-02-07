from typing import Any

from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE

from ..const import DEVICE_TRIGGER_ACTIONS_MAP, DOMAIN, HAS_EVENT_PLATFORM
from ..hass.entity import TerncyEntity
from ..types import AttrValue


class TerncyDevice:
    """目前是一个eid对应一个HA的Device，也对应Terncy那边一个profile。
    代表一个功能，比如一个四键开关就会有4个TerncyDevice
    """

    def __init__(self, did: str, eid: str, profile: int):
        """
        did (str): entityAvailable、entityDeleted、offline 事件查找设备用
        eid (str): device trigger 查找设备用
        profile (int): device trigger 查找 actions 用
        """

        self.did = did  # -00 结尾的
        self.eid = eid  # -01 -02 ... 结尾的
        self.profile = profile
        self.entities: list[TerncyEntity] = []

        # self.identifiers = {(DOMAIN, eid)}

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
                if isinstance(entity, TerncyEvent) and event_type in entity.event_types:
                    entity.trigger_event(event_type, event_attributes)
