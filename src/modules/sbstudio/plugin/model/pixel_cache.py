from collections.abc import Mapping
from typing import Iterator, Sequence

__all__ = ("PixelCache",)


class PixelCache(Mapping[str, list[float]]):
    """Mapping that associates string keys (e.g. light effect UUIDs) to pixel
    data.

    This is needed because direct pixel access with `bpy.types.Image.pixels`
    is terribly slow. The downside is that our cached pixels may become stale
    if the texture itself is updated. The user is expected to call
    `invalidate_color_image()` on the light effect if the underlying image is
    changed in a way that we cannot detect ourselves.

    The best would be to cache the pixel data on the LightEffect_ instances,
    but apparently this is not possible because Blender constructs a new
    LightEffect_ instance every time we extract a light effect from its
    collection, and by doing so we lose the cached pixels.

    The workaround is to construct a UUID for each light effect and then use
    this cache, keyed by the UUIDs, and cleaning it up periodically.
    """

    _items: dict[str, tuple[float, ...]]
    """The cached pixels, keyed by the UUIDs of the light effects."""

    def __init__(self):
        """Constructor."""
        self._items = {}

    def __delitem__(self, key: str) -> None:
        del self._items[key]

    def __getitem__(self, key: str) -> Sequence[float]:
        return self._items[key]

    def __setitem__(self, key: str, value: Sequence[float]):
        self._items[key] = tuple(value)

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def clear(self):
        """Clears all cached pixel-level representations of images."""
        self._items.clear()

    # TODO(ntamas): periodical cleanup!
