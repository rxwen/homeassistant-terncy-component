from typing import Literal, TypeVar, TypedDict

T = TypeVar("T")


class AttrValue(TypedDict):
    attr: str
    value: int


class SvcData(TypedDict):
    """DeviceData
    这个结构对应HA里的Device
    由 profile 决定里面由哪些Entity组成
    """

    id: str  # eid -01 -02 ... 结尾的
    room: str | None

    name: str | None
    profile: int
    attributes: list[AttrValue]


class PhysicalDeviceData(TypedDict):
    """一个物理设备"""

    type: Literal["device"]

    id: str  # did -00 结尾的
    # hub: str | None  # box-01-02-03-04-05-06
    room: str | None  # area-0000
    model: str

    ota: int
    version: int
    hwVersion: int

    name: str | None  # Hub version >= 3.2.14
    services: list[SvcData] | None
    online: bool


class DeviceGroupData(TypedDict):
    type: Literal["devicegroup"]
    deviceUuids: list[str]

    id: str  # eid
    room: str | None

    model: Literal["DeviceGroup"]
    ota: int
    version: int
    hwVersion: int

    name: str
    profile: int
    attributes: list[AttrValue]


class SceneActionData(TypedDict):
    id: str  # eid
    attr: str
    value: int


class SceneData(TypedDict):
    type: Literal["scene"]

    id: str  # scene-000001
    # hub: str | None  # box-01-02-03-04-05-06
    room: str | None

    model: Literal["TERNCY-SCENE"]
    name: str
    on: int  # 0 | 1
    online: bool
    actions: list[SceneActionData] | None


class RoomData(TypedDict):
    type: Literal["room"]

    id: str  # area-0000
    # hub: str | None  # box-01-02-03-04-05-06
    model: Literal["TERNCY-ROOM"]
    name: str


class UserData(TypedDict):
    type: Literal["user"]

    id: str  # user-00000003
    model: Literal["TERNCY-USER"]
    name: str


class TokenData(TypedDict):
    type: Literal["tok"]

    id: str  # token-00000022
    model: Literal["TERNCY-TOKEN"]


class TerncyEntityData(TypedDict):
    id: str  # eid
    attributes: list[AttrValue]


# report
ReportMsgData = list[TerncyEntityData]


class TerncyKeyPressedData(TypedDict):
    id: str  # eid
    attributes: list[TypedDict("Times", {"times": int})]


# keyPressed
KeyPressedMsgData = list[TerncyKeyPressedData]

# keyLongPressed, rotation: id: eid
# offline, entityDeleted: id: did
SimpleMsgData = list[TypedDict("OnlyId", {"id": str})]

# entityAvailable
EntityAvailableMsgData = list[PhysicalDeviceData | TokenData]

# entityCreated
EntityCreatedMsgData = list[SceneData | DeviceGroupData]

# entityUpdated
EntityUpdatedMsgData = list[SceneData | UserData]


class TDeviceInfo(TypedDict):
    model: str
    id: str
    version: int | None
    hwVersion: int | None
    online: bool
    room: str | None


class TSvcInfo(TypedDict):
    id: str
    name: str
    attributes: list[AttrValue] | None
    profile: int | None
