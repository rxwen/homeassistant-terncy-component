import asyncio
import json
import logging
from collections.abc import Callable, Coroutine
from itertools import groupby
from typing import ForwardRef

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    HomeAssistant,
    callback,
)
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    CONNECTION_ZIGBEE,
    format_mac,
)
from homeassistant.helpers.typing import UNDEFINED
from terncy import Terncy
from terncy.event import Connected, Disconnected, EventMessage
from terncy.terncy import _next_req_id

from .device import TerncyDevice
from .entity import TerncyEntity
from ..const import (
    ACTION_LONG_PRESS,
    ACTION_PRESSED,
    ACTION_ROTATION,
    ACTION_SINGLE_PRESS,
    CONF_DEBUG,
    CONF_DEVID,
    CONF_EXPORT_DEVICE_GROUPS,
    CONF_EXPORT_SCENES,
    CONF_IP,
    DOMAIN,
    EVENT_DATA_CLICK_TIMES,
    EVENT_DATA_SOURCE,
    EVENT_ENTITY_BUTTON_EVENTS,
    HA_CLIENT_ID,
    TERNCY_EVENT_SVC_ADD,
    TERNCY_EVENT_SVC_REMOVE,
    TERNCY_HUB_ID_PREFIX,
    TERNCY_MANU_NAME,
    TerncyEntityDescription,
)
from ..hub_monitor import TerncyHubManager
from ..profiles import PROFILES
from ..switch import TerncySwitchDescription
from ..types import (
    AttrValue,
    DeviceGroupData,
    EntityAvailableMsgData,
    EntityUpdatedMsgData,
    KeyPressedMsgData,
    PhysicalDeviceData,
    ReportMsgData,
    RoomData,
    SceneData,
    SimpleMsgData,
    SvcData,
)

_LOGGER = logging.getLogger(__name__)

SetupHandler = Callable[
    [ForwardRef("TerncyGateway"), TerncyDevice, list[TerncyEntityDescription]],
    list[TerncyEntity],
]


class TerncyGateway:
    """Represents a Terncy Gateway."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        self.hass = hass
        self.config_entry = config_entry

        self.parsed_devices: dict[str, TerncyDevice] = {}  # key: serial_number
        self.setups: dict[Platform, SetupHandler] = {}
        self._listeners: dict[str, set[Callable[[list[AttrValue]], None]]] = {}
        self.room_data: dict[str, str] = {}  # room_id: room_name
        self.scenes: dict[str, TerncyEntity] = {}  # 场景实体们

        self.name = config_entry.title
        self.mac = format_mac(config_entry.unique_id.replace(TERNCY_HUB_ID_PREFIX, ""))
        self.api = Terncy(
            HA_CLIENT_ID,
            config_entry.data["identifier"],
            config_entry.data[CONF_HOST],
            config_entry.data[CONF_PORT],
            config_entry.data[CONF_USERNAME],
            config_entry.data[CONF_TOKEN],
        )

        # region 配置项
        self.debug = config_entry.options.get(CONF_DEBUG, False)
        self.export_device_groups = config_entry.options.get(
            CONF_EXPORT_DEVICE_GROUPS, True
        )
        self.export_scenes = config_entry.options.get(CONF_EXPORT_SCENES, False)
        # endregion

        async def on_hass_stop(event: Event):
            """Stop push updates when hass stops."""
            _LOGGER.debug("STOP %s", self.unique_id)
            await self.api.stop()

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, on_hass_stop)

    def start(self):
        tern = self.api

        async def setup_terncy_loop():
            asyncio.create_task(tern.start())

        def on_terncy_svc_add(event: Event):
            """Stop push updates when hass stops."""
            dev_id = event.data[CONF_DEVID]
            if dev_id != tern.dev_id:
                return

            _LOGGER.debug("Found terncy service: %s %s", dev_id, event.data)
            ip = event.data[CONF_IP]
            if ip == "":
                _LOGGER.warning("dev %s's ip address is not valid", dev_id)
                return
            if not tern.is_connected():
                tern.ip = ip
                _LOGGER.debug("Start connecting %s %s", dev_id, tern.ip)
                self.async_create_task(setup_terncy_loop())

        def on_terncy_svc_remove(event: Event):
            """Stop push updates when hass stops."""
            _LOGGER.debug("on_terncy_svc_remove %s", event.data[CONF_DEVID])
            self.async_create_task(tern.stop())

        self.hass.bus.async_listen(TERNCY_EVENT_SVC_ADD, on_terncy_svc_add)
        self.hass.bus.async_listen(TERNCY_EVENT_SVC_REMOVE, on_terncy_svc_remove)

        hub_manager = TerncyHubManager.instance(self.hass)
        if (
            txt_records := hub_manager.hubs.get(tern.dev_id)
        ) and not tern.is_connected():
            tern.ip = txt_records[CONF_IP]
            _LOGGER.debug("Start connection to %s %s", tern.dev_id, tern.ip)
            self.async_create_task(setup_terncy_loop())

        tern.register_event_handler(self.terncy_event_handler)

    @property
    def unique_id(self):
        return self.api.dev_id

    @property
    def is_connected(self):
        return self.api.is_connected()

    def add_listener(
        self, serial_number: str, listener: Callable[[list[AttrValue]], None]
    ) -> CALLBACK_TYPE:
        @callback
        def remove_listener() -> None:
            # _LOGGER.debug("remove_listener %s", serial_number)
            if serial_number in self._listeners:
                self._listeners[serial_number].discard(listener)

        # _LOGGER.debug("add_listener %s", serial_number)
        self._listeners.setdefault(serial_number, set()).add(listener)

        return remove_listener

    def update_listeners(self, serial_number: str, data: list[AttrValue]):
        _LOGGER.debug("STATE: %s <= %s", serial_number, data)
        if serial_number in self._listeners:
            for listener in self._listeners[serial_number]:
                listener(data)
        # else:
        #     _LOGGER.debug("no listener for %s", serial_number)

    async def set_attribute(self, serial_number: str, attr: str, value, method=0):
        ret = await self.api.set_attribute(serial_number, attr, value, method)
        self.update_listeners(serial_number, [{"attr": attr, "value": value}])
        return ret

    async def set_attributes(self, serial_number: str, attrs: list[AttrValue]):
        """hack"""
        api = self.api
        if api._connection is None:
            _LOGGER.info(f"no connection with {api.dev_id}")
            return None
        req_id = _next_req_id()
        data = {
            "reqId": req_id,
            "intent": "execute",
            "entities": [
                {
                    "id": serial_number,
                    "attributes": [
                        {
                            "attr": av["attr"],
                            "value": av["value"],
                            "method": 0,
                        }
                        for av in attrs
                    ],
                }
            ],
        }
        _LOGGER.debug("api set_attributes %s", data)
        await api._connection.send(json.dumps(data))

    # region Event handlers

    def terncy_event_handler(self, api: Terncy, event):
        """Handle event from terncy system."""

        if isinstance(event, EventMessage):
            msg = event.msg
            # _LOGGER.debug("[%s] EventMessage: %s", gateway.unique_id, msg)
            if "entities" not in msg:
                _LOGGER.warning("'entities' not found in message!")
                return

            msg_data = msg.get("entities", [])
            event_type = msg.get("type")
            if event_type == "report":
                self._on_report(msg_data)
            elif event_type == "keyPressed":
                self._on_key_pressed(msg_data)
            elif event_type == "keyLongPressed":
                self._on_key_long_pressed(msg_data)
            elif event_type == "rotation":
                self._on_rotation(msg_data)
            elif event_type == "entityAvailable":
                self._on_entity_available(msg_data)
            elif event_type == "entityDeleted":
                self._on_entity_deleted(msg_data)
            elif event_type == "entityCreated":
                self._on_entity_created(msg_data)
            elif event_type == "entityUpdated":
                self._on_entity_updated(msg_data)
            elif event_type == "offline":
                self._on_offline(msg_data)
            elif event_type is None:
                _LOGGER.debug("event type is None, ignore. %s", msg)
            else:
                _LOGGER.warning(
                    "unsupported event type: %s, entities: %s",
                    event_type,
                    msg_data,
                )

        elif isinstance(event, Connected):
            # _LOGGER.debug("[%s] Connected.", gateway.unique_id)
            self.async_create_task(self.async_refresh_devices())

        elif isinstance(event, Disconnected):
            # _LOGGER.debug("[%s] Disconnected.", gateway.unique_id)
            for device in self.parsed_devices.values():
                device.set_available(False)

        else:
            _LOGGER.warning("[%s] Unknown Event: %s", self.unique_id, event)

    def _on_report(self, msg_data: ReportMsgData):
        _LOGGER.debug("EVENT: report: %s", msg_data)
        for id_attributes in msg_data:
            serial_number = id_attributes.get("id")
            attributes = id_attributes.get("attributes", [])
            self.update_listeners(serial_number, attributes)

    def _on_key_pressed(self, msg_data: KeyPressedMsgData):
        _LOGGER.debug("EVENT: keyPressed: %s", msg_data)
        device_registry = dr.async_get(self.hass)
        for entity_data in msg_data:
            if "attributes" not in entity_data:
                continue
            serial_number = entity_data["id"]
            times = entity_data["attributes"][0]["times"]
            if 1 <= times <= 9:
                event_type = EVENT_ENTITY_BUTTON_EVENTS[times]
            else:
                # never here
                event_type = ACTION_SINGLE_PRESS
            if device := self.parsed_devices.get(serial_number):
                device.trigger_event(event_type, {EVENT_DATA_CLICK_TIMES: times})
            if device_entry := device_registry.async_get_device(
                identifiers={(DOMAIN, serial_number)}
            ):
                self.hass.bus.async_fire(
                    f"{DOMAIN}_{ACTION_PRESSED}",
                    {
                        CONF_DEVICE_ID: device_entry.id,
                        EVENT_DATA_SOURCE: serial_number,
                        EVENT_DATA_CLICK_TIMES: times,
                    },
                )

    def _on_key_long_pressed(self, msg_data: SimpleMsgData):
        _LOGGER.debug("EVENT: keyLongPressed: %s", msg_data)
        device_registry = dr.async_get(self.hass)
        for item in msg_data:
            serial_number = item["id"]
            if device := self.parsed_devices.get(serial_number):
                device.trigger_event(ACTION_LONG_PRESS)
            if device_entry := device_registry.async_get_device(
                identifiers={(DOMAIN, serial_number)}
            ):
                self.hass.bus.async_fire(
                    f"{DOMAIN}_{ACTION_LONG_PRESS}",
                    {
                        CONF_DEVICE_ID: device_entry.id,
                        EVENT_DATA_SOURCE: serial_number,
                    },
                )

    def _on_rotation(self, msg_data: SimpleMsgData):
        _LOGGER.debug("EVENT: rotation: %s", msg_data)
        device_registry = dr.async_get(self.hass)
        for item in msg_data:
            serial_number = item["id"]
            if device := self.parsed_devices.get(serial_number):
                device.trigger_event(ACTION_ROTATION)
            if device_entry := device_registry.async_get_device(
                identifiers={(DOMAIN, serial_number)}
            ):
                self.hass.bus.async_fire(
                    f"{DOMAIN}_{ACTION_ROTATION}",
                    {
                        CONF_DEVICE_ID: device_entry.id,
                        EVENT_DATA_SOURCE: serial_number,
                    },
                )

    def _on_entity_available(self, msg_data: EntityAvailableMsgData):
        _LOGGER.debug("EVENT: entityAvailable: %s", msg_data)
        for device_data in msg_data:
            if device_data["type"] == "device":
                svc_list = device_data.get("services", [])
                self.setup_device(device_data, svc_list)
            else:
                _LOGGER.warning(
                    "[%s] entityAvailable: **UNSUPPORTED TYPE**: %s",
                    self.unique_id,
                    device_data,
                )

    def _on_entity_deleted(self, msg_data: SimpleMsgData):
        _LOGGER.debug("EVENT: entityDeleted: %s", msg_data)
        device_registry = dr.async_get(self.hass)
        for item in msg_data:
            device_serial = item["id"]  # device_serial or scene_id
            if device_serial.startswith("scene-"):
                if scene := self.scenes.get(device_serial):
                    scene.set_available(False)
                    self.scenes.pop(device_serial)
                    er.async_get(self.hass).async_remove(scene.entity_id)
            else:
                will_delete: dict[str, TerncyDevice] = {
                    serial_number: device
                    for serial_number, device in self.parsed_devices.items()
                    if device_serial == device.device_serial
                }
                for serial_number, device in will_delete.items():
                    device.set_available(False)
                    if device_entry := device_registry.async_get_device(
                        identifiers=device.identifiers
                    ):
                        device_registry.async_remove_device(device_entry.id)
                        _LOGGER.debug(
                            "removed device_entry: %s %s",
                            device_entry.id,
                            device_entry.name,
                        )
                    self.parsed_devices.pop(serial_number)

    def _on_entity_updated(self, msg_data: EntityUpdatedMsgData):
        _LOGGER.debug("EVENT: entityUpdated: %s", msg_data)
        for device_data in msg_data:
            if device_data["type"] == "scene":
                self.setup_scene(device_data)
            else:
                _LOGGER.info(
                    "[%s] entityUpdated: **UNSUPPORTED TYPE**: %s",
                    self.unique_id,
                    device_data,
                )

    def _on_entity_created(self, msg_data):
        _LOGGER.debug("EVENT: entityCreated: %s", msg_data)
        for device_data in msg_data:
            if device_data["type"] == "scene":
                self.setup_scene(device_data)
            else:
                _LOGGER.debug(
                    "[%s] entityCreated: **UNSUPPORTED TYPE**: %s",
                    self.unique_id,
                    device_data,
                )

    def _on_offline(self, msg_data: SimpleMsgData):
        _LOGGER.debug("EVENT: offline: %s", msg_data)
        for device_data in msg_data:
            device_serial = device_data["id"]
            for device in self.parsed_devices.values():
                if device_serial == device.device_serial:
                    device.set_available(False)

    # endregion

    # region Helpers

    @callback
    def async_create_task(self, target: Coroutine):
        return self.config_entry.async_create_task(self.hass, target)  # >=2022.7

    # endregion

    # region Setup

    def add_setup(self, platform: Platform, handler: SetupHandler):
        self.setups[platform] = handler

    def add_device(self, serial_number: str, device: TerncyDevice):
        self.parsed_devices[serial_number] = device

    def setup_device(self, device_data: PhysicalDeviceData, svc_list: list[SvcData]):
        """Got device data, create devices if not exist or update states."""

        model = device_data.get("model")
        _LOGGER.debug("[%s] setup %s: %s", self.unique_id, model, svc_list)

        device_serial = device_data["id"]
        sw_version = (
            str(device_data.get("version")) if "version" in device_data else UNDEFINED
        )
        hw_version = (
            str(device_data.get("hwVersion"))
            if "hwVersion" in device_data
            else UNDEFINED
        )
        online = device_data.get("online", True)

        suggested_area = UNDEFINED

        if device_room := device_data.get("room"):
            if device_room_name := self.room_data.get(device_room):
                suggested_area = device_room_name

        device_registry = dr.async_get(self.hass)

        if device_serial == self.unique_id:
            # update gateway details, because gateway has no svc_list
            device_registry.async_get_or_create(
                config_entry_id=self.config_entry.entry_id,
                connections={(CONNECTION_NETWORK_MAC, self.mac)},
                identifiers={(DOMAIN, self.unique_id)},
                manufacturer=TERNCY_MANU_NAME,
                model=model,
                name=self.name,
                sw_version=sw_version,
                hw_version=hw_version,
                suggested_area=suggested_area,
            )

        for svc in svc_list:
            serial_number = svc["id"]
            name = svc["name"] or serial_number  # some name is ""
            attributes = svc.get("attributes", [])

            device = self.parsed_devices.get(serial_number)
            if not device:
                _LOGGER.debug("[%s] new device: %s %s", device_serial, serial_number)

                profile = svc.get("profile")
                device = TerncyDevice(device_serial, serial_number, profile)
                self.add_device(serial_number, device)

                if profile in PROFILES:
                    if svc_room := svc.get("room"):
                        if svc_room_name := self.room_data.get(svc_room):
                            suggested_area = svc_room_name
                    device_registry.async_get_or_create(
                        config_entry_id=self.config_entry.entry_id,
                        connections={(CONNECTION_ZIGBEE, serial_number)},
                        identifiers={(DOMAIN, serial_number)},
                        manufacturer=TERNCY_MANU_NAME,
                        model=model,
                        name=name,
                        sw_version=sw_version,
                        hw_version=hw_version,
                        suggested_area=suggested_area,
                        via_device=(DOMAIN, self.unique_id),
                    )
                    all_descriptions = PROFILES.get(profile)
                    for plat, descs in groupby(all_descriptions, lambda x: x.PLATFORM):
                        entities = self.setups[plat](self, device, descs)
                        device.entities.extend(entities)
                else:
                    _LOGGER.debug("[%s] Unsupported profile:%d", serial_number, profile)

            # update states
            device.set_available(online)
            device.update_state(attributes)

    async def _fetch_data(self, ent_type: str) -> list:
        response = await self.api.get_entities(ent_type, True)
        if "rsp" not in response:
            _LOGGER.warning("fetch %s error, response: %s", ent_type, response)
        return response.get("rsp", {}).get("entities", [])

    async def async_refresh_devices(self):
        """Get devices from terncy."""
        _LOGGER.debug("[%s] Refresh devices now.", self.unique_id)

        # room
        try:
            rooms: list[RoomData] = await self._fetch_data("room")
            # _LOGGER.debug("[%s] got rooms %s", self.unique_id, rooms)
            self.room_data = {room["id"]: room["name"] for room in rooms}
        except Exception as e:
            _LOGGER.warning("fetch room error: %s", e)

        # device
        devices: list[PhysicalDeviceData] = await self._fetch_data("device")
        # _LOGGER.debug("[%s] got devices %s", self.unique_id, devices)

        for device_data in devices:
            svc_list = device_data.get("services", [])
            self.setup_device(device_data, svc_list)

        # device group
        device_groups: list[DeviceGroupData] = await self._fetch_data("devicegroup")
        # _LOGGER.debug("[%s] got device_groups %s", self.unique_id, device_groups)

        if self.export_device_groups:
            for device_group_data in device_groups:
                svc_list = [device_group_data]
                self.setup_device(device_group_data, svc_list)

        # scene
        scenes: list[SceneData] = await self._fetch_data("scene")
        _LOGGER.debug("[%s] got scene response: %s", self.unique_id, scenes)

        if self.export_scenes:
            # 创建一个共用的设备，里面放所有的场景开关
            device_registry = dr.async_get(self.hass)
            device_registry.async_get_or_create(
                config_entry_id=self.config_entry.entry_id,
                identifiers={(DOMAIN, f"{self.unique_id}_scenes")},
                manufacturer=TERNCY_MANU_NAME,
                model="TERNCY-SCENE",
                name="TERNCY-SCENE",
                via_device=(DOMAIN, self.unique_id),
            )
            for scene_data in scenes:
                self.setup_scene(scene_data)

    def setup_scene(self, scene_data: SceneData):
        if not self.export_scenes:
            return
        if len(scene_data.get("actions", [])) == 0:
            # ignore scene without actions
            return

        scene_id = scene_data["id"]
        _LOGGER.debug("[%s] setup %s %s", self.unique_id, scene_id, scene_data)

        name = scene_data.get("name") or scene_id  # some name is ""
        online = scene_data.get("online", True)

        attributes: list[AttrValue] = []
        if "on" in scene_data:
            attributes.append({"attr": "on", "value": scene_data["on"]})

        entity = self.scenes.get(scene_id)
        if not entity:
            descriptions = [
                TerncySwitchDescription(
                    key="scene",
                    name=name,
                    icon="mdi:palette",
                    unique_id_prefix=self.unique_id,  # 融合网关可能会有重复的scene_id，加个网关id作前缀
                )
            ]
            fake_device = FakeSceneDevice(
                scene_id, {(DOMAIN, f"{self.unique_id}_scenes")}
            )
            entities = self.setups[Platform.SWITCH](self, fake_device, descriptions)
            entity = entities[0]
            self.scenes[scene_id] = entity
        else:
            entity.entity_description.name = name

        entity.set_available(online)
        entity.update_state(attributes)

    # endregion


class FakeSceneDevice:
    """临时方案，后续再调整"""

    def __init__(self, serial_number: str, identifiers):
        self.serial_number = serial_number
        self.identifiers = identifiers
