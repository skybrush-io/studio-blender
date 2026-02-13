from typing import Any, Callable, Sequence, Type, TypeAlias, TypeVar

from bpy.types import bpy_prop_collection_idprop

_T = TypeVar("_T")

_EnumItem: TypeAlias = (
    tuple[str, str, str]
    | tuple[str, str, str, int]
    | tuple[str, str, str, str, int]
    | None
)
_PropertyDeferred: TypeAlias = tuple

def BoolProperty(
    *,
    name: str = ...,
    description: str = ...,
    default: bool = ...,
    options: set[str] = ...,
    update: Callable[[Any, Any], None] | None = ...,
    get: Callable[[Any], bool] | None = ...,
    set: Callable[[Any, bool], None] | None = ...,
) -> bool: ...
def CollectionProperty(
    type: Type[_T], **kwargs: Any
) -> bpy_prop_collection_idprop[_T]: ...
def EnumProperty(
    *,
    name: str = ...,
    description: str = ...,
    items: Sequence[_EnumItem] | Callable[[Any, Any], Sequence[_EnumItem]] = ...,
    default: _T | int = ...,
    options: set[str] = ...,
    update: Callable[[Any, Any], None] | None = ...,
    get: Callable[[Any], str] | None = ...,
    set: Callable[[Any, str], None] | None = ...,
) -> _T: ...
def FloatProperty(
    *,
    name: str = ...,
    description: str = ...,
    default: float = ...,
    min: float = ...,
    max: float = ...,
    soft_min: float = ...,
    soft_max: float = ...,
    step: int = ...,
    precision: int = ...,
    options: set[str] = ...,
    subtype: str = ...,
    unit: str = ...,
    update: Callable[[Any, Any], None] | None = ...,
    get: Callable[[Any], float] | None = ...,
    set: Callable[[Any, float], None] | None = ...,
) -> float: ...
def FloatVectorProperty(
    *,
    name: str = ...,
    description: str = ...,
    default: Sequence[float] = ...,
    size: int = ...,
    min: float = ...,
    max: float = ...,
    soft_min: float = ...,
    soft_max: float = ...,
    step: int = ...,
    precision: int = ...,
    options: set[str] = ...,
    subtype: str = ...,
    unit: str = ...,
    update: Callable[[Any, Any], None] | None = ...,
    get: Callable[[Any], Sequence[float]] | None = ...,
    set: Callable[[Any, Sequence[float]], None] | None = ...,
) -> tuple[float]: ...
def IntProperty(
    *,
    name: str = ...,
    description: str = ...,
    default: int = ...,
    min: int = ...,
    max: int = ...,
    soft_min: int = ...,
    soft_max: int = ...,
    step: int = ...,
    options: set[str] = ...,
    subtype: str = ...,
    update: Callable[[Any, Any], None] | None = ...,
    get: Callable[[Any], int] | None = ...,
    set: Callable[[Any, int], None] | None = ...,
) -> int: ...
def PointerProperty(
    *,
    name: str = ...,
    description: str = ...,
    type: Type[_T],
    options: set[str] = ...,
    poll: Callable[[Any, _T], bool] | None = ...,
    update: Callable[[Any, Any], None] | None = ...,
) -> _T: ...
def StringProperty(
    *,
    name: str = ...,
    description: str = ...,
    default: str = ...,
    maxlen: int = ...,
    options: set[str] = ...,
    subtype: str = ...,
    update: Callable[[Any, Any], None] | None = ...,
    get: Callable[[Any], str] | None = ...,
    set: Callable[[Any, str], None] | None = ...,
) -> str: ...
