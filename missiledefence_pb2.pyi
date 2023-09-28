from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SoldierFilter(_message.Message):
    __slots__ = ["soldier_id"]
    SOLDIER_ID_FIELD_NUMBER: _ClassVar[int]
    soldier_id: int
    def __init__(self, soldier_id: _Optional[int] = ...) -> None: ...

class CommanderStatus(_message.Message):
    __slots__ = ["new_commander_id"]
    NEW_COMMANDER_ID_FIELD_NUMBER: _ClassVar[int]
    new_commander_id: int
    def __init__(self, new_commander_id: _Optional[int] = ...) -> None: ...

class NewCommanderFilter(_message.Message):
    __slots__ = ["soldier_id"]
    SOLDIER_ID_FIELD_NUMBER: _ClassVar[int]
    soldier_id: int
    def __init__(self, soldier_id: _Optional[int] = ...) -> None: ...

class ConnectionRequest(_message.Message):
    __slots__ = ["soldier_id", "position", "no_of_soldiers", "warzone_size"]
    SOLDIER_ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    NO_OF_SOLDIERS_FIELD_NUMBER: _ClassVar[int]
    WARZONE_SIZE_FIELD_NUMBER: _ClassVar[int]
    soldier_id: int
    position: _containers.RepeatedScalarFieldContainer[int]
    no_of_soldiers: int
    warzone_size: int
    def __init__(self, soldier_id: _Optional[int] = ..., position: _Optional[_Iterable[int]] = ..., no_of_soldiers: _Optional[int] = ..., warzone_size: _Optional[int] = ...) -> None: ...

class NewCommanderDetails(_message.Message):
    __slots__ = ["soldier_id", "position", "speed"]
    SOLDIER_ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    soldier_id: int
    position: _containers.RepeatedScalarFieldContainer[int]
    speed: int
    def __init__(self, soldier_id: _Optional[int] = ..., position: _Optional[_Iterable[int]] = ..., speed: _Optional[int] = ...) -> None: ...

class Empty(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class WasHit(_message.Message):
    __slots__ = ["soldier_id", "is_alive", "position"]
    SOLDIER_ID_FIELD_NUMBER: _ClassVar[int]
    IS_ALIVE_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    soldier_id: int
    is_alive: bool
    position: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, soldier_id: _Optional[int] = ..., is_alive: bool = ..., position: _Optional[_Iterable[int]] = ...) -> None: ...

class MissileDetails(_message.Message):
    __slots__ = ["position", "time", "type"]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    position: _containers.RepeatedScalarFieldContainer[int]
    time: int
    type: str
    def __init__(self, position: _Optional[_Iterable[int]] = ..., time: _Optional[int] = ..., type: _Optional[str] = ...) -> None: ...

class LayoutRow(_message.Message):
    __slots__ = ["row"]
    ROW_FIELD_NUMBER: _ClassVar[int]
    row: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, row: _Optional[_Iterable[int]] = ...) -> None: ...

class MissileApproaching(_message.Message):
    __slots__ = ["missile", "layout"]
    MISSILE_FIELD_NUMBER: _ClassVar[int]
    LAYOUT_FIELD_NUMBER: _ClassVar[int]
    missile: MissileDetails
    layout: _containers.RepeatedCompositeFieldContainer[LayoutRow]
    def __init__(self, missile: _Optional[_Union[MissileDetails, _Mapping]] = ..., layout: _Optional[_Iterable[_Union[LayoutRow, _Mapping]]] = ...) -> None: ...
