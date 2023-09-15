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

    id: str  # serial_number -01 -02 ... 结尾的
    room: str | None

    name: str | None
    profile: int
    attributes: list[AttrValue]


class PhysicalDeviceData(TypedDict):
    """一个物理设备"""

    type: Literal["device"]

    id: str  # device_serial -00 结尾的
    room: str | None  # area-0000
    model: str

    ota: int
    version: int
    hwVersion: int

    services: list[SvcData] | None
    online: bool


class DeviceGroupData(TypedDict):
    type: Literal["devicegroup"]
    deviceUuids: list[str]

    id: str  # serial_number
    room: str | None

    model: Literal["DeviceGroup"]
    ota: int
    version: int
    hwVersion: int

    name: str
    profile: int
    attributes: list[AttrValue]


class SceneActionData(TypedDict):
    id: str  # serial_number
    attr: str
    value: int


class SceneData(TypedDict):
    type: Literal["scene"]

    id: str  # scene-000001
    room: str | None

    model: Literal["TERNCY-SCENE"]
    name: str
    on: int  # 0 | 1
    online: bool
    actions: list[SceneActionData] | None


class TerncyTokenData(TypedDict):
    type: Literal["token"]
    id: str
    model: str


class TerncyEntityData(TypedDict):
    id: str  # serial_number
    attributes: list[AttrValue]


# report
ReportMsgData = list[TerncyEntityData]


class TerncyKeyPressedData(TypedDict):
    id: str  # serial_number
    attributes: list[TypedDict("Times", {"times": int})]


# keyPressed
KeyPressedMsgData = list[TerncyKeyPressedData]

# keyLongPressed, rotation: id: serial_number
# offline, entityDeleted: id: device_serial
SimpleMsgData = list[TypedDict("OnlyId", {"id": str})]

# entityAvailable
EntityAvailableMsgData = list[PhysicalDeviceData | TerncyTokenData]

# entityCreated
EntityCreatedMsgData = list[SceneData]

# entityUpdated
EntityUpdatedMsgData = list[SceneData | TerncyTokenData]