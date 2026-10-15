"""Event platform support for Terncy. HA>=2023.8"""

import logging
from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import (
    ACTION_LONG_PRESS,
    ACTION_SINGLE_PRESS,
    EVENT_DATA_CLICK_TIMES,
    EVENT_ENTITY_BUTTON_EVENTS,
    HAS_BUTTON_EVENT_TYPE,
    LONG_PRESS_RELEASE_TIMEOUT,
)
from .hass.entity import TerncyEntity
from .hass.entity_descriptions import TerncyEventDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    TerncyEntity.ADD[f"{entry.entry_id}.event"] = async_add_entities


class TerncyEvent(TerncyEntity, EventEntity):
    """Represents a Terncy Button."""

    entity_description: TerncyEventDescription

    @property
    def source_event_types(self) -> list[str]:
        """要监听的设备事件类型"""
        return self.event_types

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if device := self.gateway.parsed_devices.get(self.eid):
            for event_type in self.source_event_types:
                self.async_on_remove(
                    device.add_event_listener(event_type, self.trigger_event)
                )

    def update_state(self, attrs):
        # _LOGGER.debug("%s <= %s", self.eid, attrs)
        # do nothing
        pass

    def trigger_event(
        self, event_type: str, event_attributes: dict[str, Any] | None = None
    ) -> None:
        self._trigger_event(event_type, event_attributes)
        self.async_write_ha_state()


TerncyEntity.NEW["event"] = TerncyEvent

if HAS_BUTTON_EVENT_TYPE:
    from homeassistant.components.event import ATTR_MULTI_PRESS_COUNT, ButtonEventType

    class TerncyStdButtonEvent(TerncyEvent):
        """把小燕的按键事件转换成 HA 标准事件类型（ButtonEventType）

        长按：网关在按住 1 秒后开始每秒上报一次 long_press，没有松开事件，
        所以第一次上报时发 LONG_PRESS_START，之后的上报只用来续期，
        超过 LONG_PRESS_RELEASE_TIMEOUT 秒没有新的上报就认为已经松开，发 LONG_PRESS_END。
        有的设备松开时还会再报一次 single_press，这时直接当作松开处理，并丢弃这次单击。
        """

        _cancel_long_press_end: CALLBACK_TYPE | None = None

        @property
        def source_event_types(self) -> list[str]:
            return EVENT_ENTITY_BUTTON_EVENTS

        async def async_added_to_hass(self) -> None:
            await super().async_added_to_hass()
            self.async_on_remove(self._cancel_long_press_timer)

        @callback
        def _cancel_long_press_timer(self) -> None:
            if self._cancel_long_press_end:
                self._cancel_long_press_end()
                self._cancel_long_press_end = None

        @callback
        def _end_long_press(self, _now=None) -> None:
            self._cancel_long_press_timer()
            super().trigger_event(ButtonEventType.LONG_PRESS_END)

        def trigger_event(
            self, event_type: str, event_attributes: dict[str, Any] | None = None
        ) -> None:
            if event_type == ACTION_LONG_PRESS:
                if self._cancel_long_press_end:
                    # 按住期间的重复上报，只续期
                    self._cancel_long_press_end()
                else:
                    super().trigger_event(ButtonEventType.LONG_PRESS_START)
                self._cancel_long_press_end = async_call_later(
                    self.hass, LONG_PRESS_RELEASE_TIMEOUT, self._end_long_press
                )
            elif self._cancel_long_press_end:
                # 长按中收到的单击是松开时上报的，不当作单击
                self._end_long_press()
            elif event_type == ACTION_SINGLE_PRESS:
                super().trigger_event(ButtonEventType.PRESS_END)
            else:
                times = (event_attributes or {}).get(EVENT_DATA_CLICK_TIMES)
                if times is None:  # never here
                    times = EVENT_ENTITY_BUTTON_EVENTS.index(event_type)
                super().trigger_event(
                    ButtonEventType.MULTI_PRESS_END,
                    {ATTR_MULTI_PRESS_COUNT: times},
                )

    TerncyEntity.NEW["event.key.event_std_button"] = TerncyStdButtonEvent
