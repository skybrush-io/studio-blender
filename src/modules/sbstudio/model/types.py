from collections.abc import MutableSequence
from typing import Generic, Mapping, Protocol, Sequence, TypeAlias, TypeVar, overload

from numpy.typing import NDArray

__all__ = (
    "Color",
    "ColorLike",
    "Coordinate3D",
    "Jsonable",
    "MutableRGBColor",
    "RGBAColor",
    "RGBColor",
    "RGBAColorLike",
    "RGBColorLike",
    "Rotation3D",
    "SupportsForEach",
    "Quaternion",
)


Coordinate3D: TypeAlias = tuple[float, float, float]
"""Type alias for simple 3D coordinates."""

RGBColor: TypeAlias = tuple[float, float, float]
"""Type alias for RGB color tuples used by Blender."""

MutableRGBColor: TypeAlias = MutableSequence[float]
"""Type alias for RGB color components that can be mutated in-place."""

RGBColorLike: TypeAlias = RGBColor | MutableRGBColor
"""Type alias for mutable or immutable RGB colors."""

RGBAColor: TypeAlias = tuple[float, float, float, float]
"""Type alias for RGBA color tuples used by Blender."""

MutableRGBAColor: TypeAlias = MutableSequence[float]
"""Type alias for RGBA color components that can be mutated in-place."""

RGBAColorLike: TypeAlias = RGBAColor | MutableRGBAColor
"""Type alias for mutable or immutable RGBA colors."""

Color: TypeAlias = RGBColor | RGBAColor
"""Type alias for immutable colors, either RGB or RGBA."""

ColorLike: TypeAlias = RGBColorLike | RGBAColorLike
"""Type alias for mutable or immutable colors, either RGB or RGBA."""

Rotation3D: TypeAlias = tuple[float, float, float]
"""Type alias for simple 3D rotations."""

Quaternion: TypeAlias = tuple[float, float, float, float]
"""Type alias for 4D quaternions."""


T = TypeVar("T")


class SupportsForEach(Generic[T], Protocol):
    """Protocol for objects that support the `foreach_get()` and `foreach_set()`
    methods.

    Used only in type annotations.
    """

    @overload
    def foreach_get(self, attr: str, seq: MutableSequence[T]) -> None: ...
    @overload
    def foreach_get(self, attr: str, seq: NDArray) -> None: ...
    @overload
    def foreach_set(self, attr: str, seq: Sequence[T]) -> None: ...
    @overload
    def foreach_set(self, attr: str, seq: NDArray) -> None: ...
    def __len__(self) -> int: ...


Jsonable: TypeAlias = (
    int | float | bool | None | str | Sequence["Jsonable"] | Mapping[str, "Jsonable"]
)
"""Type alias for types that can be stored in a plain JSON file."""
