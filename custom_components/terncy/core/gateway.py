import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import ForwardRef

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    MAJOR_VERSION,
    MINOR_VERSION,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    CONNECTION_ZIGBEE,
    format_mac,
)

if (MAJOR_VERSION, MINOR_VERSION) >= (2023, 9):
    from homeassistant.helpers.device_registry import DeviceInfo
else:
    from homeassistant.helpers.entity import DeviceInfo

from homeassistant.helpers.typing import UNDEFINED
from terncy import Terncy
from terncy.event import Connected, Disconnected, EventMessage

from .device import TerncyDevice
from ..const import (
    ACTION_LONG_PRESS,
    ACTION_PRESSED,
    ACTION_ROTATION,
    ACTION_SINGLE_PRESS,
    CONF_DEVID,
    CONF_EXPORT_DEVICE_GROUPS,
    CONF_EXPORT_SCENES,
    CONF_IP,
    DEFAULT_ROOMS,
    DOMAIN,
    EVENT_DATA_CLICK_TIMES,
    EVENT_DATA_SOURCE,
    EVENT_ENTITY_BUTTON_EVENTS,
    HA_CLIENT_ID,
    TERNCY_EVENT_SVC_ADD,
    TERNCY_EVENT_SVC_RECONNECT,
    TERNCY_EVENT_SVC_REMOVE,
    TERNCY_HUB_ID_PREFIX,
    TERNCY_MANU_NAME,
)
from ..hass.add_entities import create_entity, ha_add_entity
from ..hass.entity import TerncyEntity
from ..hass.entity_descriptions import TerncyEntityDescription, TerncySwitchDescription
from ..hub_monitor import TerncyHubManager
from ..profiles import PROFILES
from ..types import (
    AttrValue,
    DeviceGroupData,
    EntityAvailableMsgData,
    EntityCreatedMsgData,
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
    [
        ForwardRef("TerncyGateway"),
        set[tuple[str, str]],  # device_identifiers
        str,  # eid
        list[TerncyEntityDescription],
        list[AttrValue],  # attributes
    ],
    list[TerncyEntity],
]


class TerncyGateway:
    """Represents a Terncy Gateway."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        self.hass = hass
        self.config_entry = config_entry

        self.parsed_devices: dict[str, TerncyDevice] = {}  # key: eid
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
        tern.retry = True

        async def setup_terncy_loop():
            asyncio.create_task(tern.start())

        def on_terncy_svc_add(event: Event):
            """Terncy service found handler"""
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
                tern.retry = True
                self.async_create_task(setup_terncy_loop())

        async def on_terncy_svc_reconnect(event: Event):
            """Terncy service retry connection handler"""
            dev_id = event.data[CONF_DEVID]
            if dev_id != tern.dev_id:
                return
            if not tern.retry:
                _LOGGER.warning("service %s %s stopped, don't retry", dev_id, tern.ip)
                return

            _LOGGER.warning(
                "Reconnect terncy service: %s %s to wait", dev_id, event.data
            )
            await asyncio.sleep(2)
            _LOGGER.warning(
                "Reconnect terncy service: %s %s after wait", dev_id, event.data
            )
            if not tern.is_connected():
                _LOGGER.warning("Start connecting %s %s", dev_id, tern.ip)
                self.async_create_task(setup_terncy_loop())
            else:
                _LOGGER.warning(
                    "service %s %s is still connected while retry", dev_id, event.data
                )

        def on_terncy_svc_remove(event: Event):
            """Terncy service stop handler"""
            dev_id = event.data[CONF_DEVID]
            if dev_id != tern.dev_id:
                return

            _LOGGER.debug("on_terncy_svc_remove %s", event.data[CONF_DEVID])
            self.async_create_task(tern.stop())
            tern.retry = False

        self.hass.bus.async_listen(TERNCY_EVENT_SVC_ADD, on_terncy_svc_add)
        self.hass.bus.async_listen(TERNCY_EVENT_SVC_RECONNECT, on_terncy_svc_reconnect)
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
        return self.api.dev_id  # box-12-34-56-78-90-ab

    @property
    def is_connected(self):
        return self.api.is_connected()

    def add_listener(
        self, eid: str, listener: Callable[[list[AttrValue]], None]
    ) -> CALLBACK_TYPE:
        @callback
        def remove_listener() -> None:
            # _LOGGER.debug("[%s] remove_listener %s", self.unique_id, eid)
            if eid in self._listeners:
                self._listeners[eid].discard(listener)

        # _LOGGER.debug("[%s] add_listener %s", self.unique_id, eid)
        self._listeners.setdefault(eid, set()).add(listener)

        return remove_listener

    def update_listeners(self, eid: str, data: list[AttrValue]):
        # _LOGGER.debug("[%s] STATE: %s <= %s", self.unique_id, eid, data)
        if eid in self._listeners:
            for listener in self._listeners[eid]:
                listener(data)
        # else:
        #     _LOGGER.debug("[%s] no listener for %s", self.unique_id, eid)

    async def set_attribute(self, eid: str, attr: str, value, method=0):
        await self.api.set_attribute(eid, attr, value, method)
        self.update_listeners(eid, [{"attr": attr, "value": value}])

    async def set_attributes(self, eid: str, attrs: list[AttrValue], method=0):
        await self.api.set_attributes(eid, attrs, method)
        self.update_listeners(eid, attrs)

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
                _LOGGER.debug(
                    "[%s] event type is None, ignore. %s", self.unique_id, msg
                )
            else:
                _LOGGER.warning(
                    "[%s] unsupported event type: %s, entities: %s",
                    self.unique_id,
                    event_type,
                    msg_data,
                )

        elif isinstance(event, Connected):
            _LOGGER.info("[%s] Connected.", api.dev_id)
            self.async_create_task(self.async_refresh_devices())

        elif isinstance(event, Disconnected):
            _LOGGER.warning("[%s] Disconnected.", api.dev_id)
            for device in self.parsed_devices.values():
                device.set_available(False)
            txt_records = {CONF_DEVID: api.dev_id}
            self.hass.bus.async_fire(TERNCY_EVENT_SVC_RECONNECT, txt_records)

        else:
            _LOGGER.warning("[%s] Unknown Event: %s", self.unique_id, event)

    def _on_report(self, msg_data: ReportMsgData):
        _LOGGER.debug("[%s] EVENT: report: %s", self.unique_id, msg_data)
        for id_attributes in msg_data:
            eid = id_attributes.get("id")
            attributes = id_attributes.get("attributes", [])
            self.update_listeners(eid, attributes)

    def _on_key_pressed(self, msg_data: KeyPressedMsgData):
        _LOGGER.debug("[%s] EVENT: keyPressed: %s", self.unique_id, msg_data)
        device_registry = dr.async_get(self.hass)
        for entity_data in msg_data:
            if "attributes" not in entity_data:
                continue
            eid = entity_data["id"]
            times = entity_data["attributes"][0]["times"]
            if 1 <= times <= 9:
                event_type = EVENT_ENTITY_BUTTON_EVENTS[times]
            else:
                # never here
                event_type = ACTION_SINGLE_PRESS
            if device := self.parsed_devices.get(eid):
                device.trigger_event(event_type, {EVENT_DATA_CLICK_TIMES: times})
            if device_entry := device_registry.async_get_device(
                identifiers={(DOMAIN, eid)}
            ):
                self.hass.bus.async_fire(
                    f"{DOMAIN}_{ACTION_PRESSED}",
                    {
                        CONF_DEVICE_ID: device_entry.id,
                        EVENT_DATA_SOURCE: eid,
                        EVENT_DATA_CLICK_TIMES: times,
                    },
                )

    def _on_key_long_pressed(self, msg_data: SimpleMsgData):
        _LOGGER.debug("[%s] EVENT: keyLongPressed: %s", self.unique_id, msg_data)
        device_registry = dr.async_get(self.hass)
        for item in msg_data:
            eid = item["id"]
            if device := self.parsed_devices.get(eid):
                device.trigger_event(ACTION_LONG_PRESS)
            if device_entry := device_registry.async_get_device(
                identifiers={(DOMAIN, eid)}
            ):
                self.hass.bus.async_fire(
                    f"{DOMAIN}_{ACTION_LONG_PRESS}",
                    {
                        CONF_DEVICE_ID: device_entry.id,
                        EVENT_DATA_SOURCE: eid,
                    },
                )

    def _on_rotation(self, msg_data: SimpleMsgData):
        _LOGGER.debug("[%s] EVENT: rotation: %s", self.unique_id, msg_data)
        device_registry = dr.async_get(self.hass)
        for item in msg_data:
            eid = item["id"]
            if device := self.parsed_devices.get(eid):
                device.trigger_event(ACTION_ROTATION)
            if device_entry := device_registry.async_get_device(
                identifiers={(DOMAIN, eid)}
            ):
                self.hass.bus.async_fire(
                    f"{DOMAIN}_{ACTION_ROTATION}",
                    {
                        CONF_DEVICE_ID: device_entry.id,
                        EVENT_DATA_SOURCE: eid,
                    },
                )

    def _on_entity_available(self, msg_data: EntityAvailableMsgData):
        _LOGGER.debug("[%s] EVENT: entityAvailable: %s", self.unique_id, msg_data)
        for device_data in msg_data:
            if device_data["type"] == "device":
                svc_list = device_data.get("services", [])
                self.setup_device(device_data, svc_list)
            elif device_data["type"] == "token":
                # do nothing
                pass
            else:
                _LOGGER.warning(
                    "[%s] entityAvailable: **UNSUPPORTED TYPE**: %s",
                    self.unique_id,
                    device_data,
                )

    def _on_entity_deleted(self, msg_data: SimpleMsgData):
        _LOGGER.debug("[%s] EVENT: entityDeleted: %s", self.unique_id, msg_data)
        device_registry = dr.async_get(self.hass)
        for item in msg_data:
            did = item["id"]  # did or scene_id
            if did.startswith("scene-"):
                if scene := self.scenes.get(did):
                    scene.set_available(False)
                    self.scenes.pop(did)
                    er.async_get(self.hass).async_remove(scene.entity_id)
            else:
                will_delete: dict[str, TerncyDevice] = {
                    eid: device
                    for eid, device in self.parsed_devices.items()
                    if did == device.did
                }
                for eid, device in will_delete.items():
                    device.set_available(False)
                    if device_entry := device_registry.async_get_device(
                        identifiers={(DOMAIN, eid)}
                    ):
                        device_registry.async_remove_device(device_entry.id)
                        _LOGGER.debug(
                            "[%s] removed device_entry: %s %s",
                            self.unique_id,
                            device_entry.id,
                            device_entry.name,
                        )
                    self.parsed_devices.pop(eid)

    def _on_entity_updated(self, msg_data: EntityUpdatedMsgData):
        _LOGGER.debug("[%s] EVENT: entityUpdated: %s", self.unique_id, msg_data)
        for item in msg_data:
            if item["type"] == "scene":
                self.setup_scene(item)
            elif item["type"] == "user":
                _LOGGER.debug("[%s] type user, ignore.", self.unique_id)
            else:
                _LOGGER.info(
                    "[%s] entityUpdated: **UNSUPPORTED TYPE**: %s",
                    self.unique_id,
                    item,
                )

    def _on_entity_created(self, msg_data: EntityCreatedMsgData):
        _LOGGER.debug("[%s] EVENT: entityCreated: %s", self.unique_id, msg_data)
        for item in msg_data:
            if item["type"] == "scene":
                self.setup_scene(item)
            elif item["type"] == "devicegroup":
                self.setup_device_group(item)
            else:
                _LOGGER.debug(
                    "[%s] entityCreated: **UNSUPPORTED TYPE**: %s",
                    self.unique_id,
                    item,
                )

    def _on_offline(self, msg_data: SimpleMsgData):
        _LOGGER.debug("[%s] EVENT: offline: %s", self.unique_id, msg_data)
        for device_data in msg_data:
            did = device_data["id"]
            for device in self.parsed_devices.values():
                if did == device.did:
                    device.set_available(False)

    # endregion

    # region Helpers

    @callback
    def async_create_task(self, target: Coroutine):
        return self.config_entry.async_create_task(self.hass, target)

    # endregion

    # region Setup

    def add_device(self, eid: str, device: TerncyDevice):
        self.parsed_devices[eid] = device

    def setup_device_group(self, device_group_data: DeviceGroupData):
        # noinspection PyTypeChecker
        self.setup_device(device_group_data, [device_group_data])

    def setup_device(self, device_data: PhysicalDeviceData, svc_list: list[SvcData]):
        """Got device data, create devices if not exist or update states."""

        model = device_data.get("model")
        _LOGGER.debug("[%s] setup %s: %s", self.unique_id, model, svc_list)

        did = device_data["id"]
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

        if did == self.unique_id:
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
            eid = svc["id"]
            name = svc["name"]
            if not name:  # some name is ""
                if device_name := device_data.get("name"):
                    name = f"{device_name}-{eid[-2:]}"  # 'device_name-04'
                else:
                    name = eid
            attributes = svc.get("attributes", [])

            device = self.parsed_devices.get(eid)
            if not device:
                # _LOGGER.debug("[%s] New device: %s %s", self.unique_id, did, eid)

                profile = svc.get("profile")
                device = TerncyDevice(did, eid, profile)

                if profile in PROFILES:
                    if svc_room := svc.get("room"):
                        if svc_room_name := self.room_data.get(svc_room):
                            suggested_area = svc_room_name
                    attrs = [a["attr"] for a in attributes]
                    descriptions = [
                        description
                        for description in PROFILES.get(profile)
                        if (
                            not description.required_attrs
                            or set(description.required_attrs).issubset(attrs)
                        )
                    ]
                    if len(descriptions) > 0:
                        identifiers = {(DOMAIN, eid)}
                        device_registry.async_get_or_create(
                            config_entry_id=self.config_entry.entry_id,
                            connections={(CONNECTION_ZIGBEE, eid)},
                            identifiers=identifiers,
                            manufacturer=TERNCY_MANU_NAME,
                            model=model,
                            name=name,
                            sw_version=sw_version,
                            hw_version=hw_version,
                            suggested_area=suggested_area,
                            via_device=(DOMAIN, self.unique_id),
                        )
                        self.add_device(eid, device)
                        for description in descriptions:
                            entity = create_entity(self, eid, description, attributes)
                            entity._attr_device_info = DeviceInfo(
                                identifiers=identifiers
                            )
                            ha_add_entity(self.hass, self.config_entry, entity)
                            device.entities.append(entity)
                else:
                    _LOGGER.debug(
                        "[%s] Unsupported profile:%d %s", eid, profile, attributes
                    )

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
        _LOGGER.debug("[%s] Fetching data...", self.unique_id)

        # room
        lang = self.hass.config.language  # HA>=2022.12
        default_rooms = DEFAULT_ROOMS.get(lang, DEFAULT_ROOMS.get("en"))
        try:
            rooms: list[RoomData] = await self._fetch_data("room")
            self.room_data = {
                room["id"]: room["name"] or default_rooms.get(room["id"], "")
                for room in rooms
            }
            _LOGGER.debug("[%s] ROOM %s: %s", self.unique_id, lang, self.room_data)
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
                self.setup_device_group(device_group_data)

        # scene
        scenes: list[SceneData] = await self._fetch_data("scene")
        _LOGGER.debug("[%s] SCENE: %s", self.unique_id, scenes)

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

        scene_id = scene_data["id"]

        if len(scene_data.get("actions", [])) == 0:
            # ignore scene without actions
            if entity := self.scenes.get(scene_id):
                # if already exist, disable it
                entity.set_available(False)
            return

        _LOGGER.debug("[%s] setup %s %s", self.unique_id, scene_id, scene_data)

        name = scene_data.get("name") or scene_id  # some name is ""
        online = scene_data.get("online", True)

        entity = self.scenes.get(scene_id)
        init_states = [{"attr": "on", "value": scene_data["on"]}]
        if not entity:
            description = TerncySwitchDescription(
                key="scene",
                name=name,
                icon="mdi:palette",
                unique_id_prefix=self.unique_id,  # scene_id不是uuid形式的，加个网关id作前缀
            )
            identifiers = {(DOMAIN, f"{self.unique_id}_scenes")}
            entity = create_entity(self, scene_id, description, init_states)
            entity._attr_device_info = DeviceInfo(identifiers=identifiers)
            ha_add_entity(self.hass, self.config_entry, entity)
            self.scenes[scene_id] = entity
        else:
            entity._attr_name = name

        entity.set_available(online)
        entity.update_state(init_states)

    # endregion
