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

    _dynamic_keys: set[str]
    """Set of keys that are not static (i.e. they are invalidated when the
    current frame changes).
    """

    def __init__(self):
        """Constructor."""
        self._dynamic_keys = set()
        self._items = {}

    def add(self, key: str, value: Sequence[float], *, is_static: bool = False):
        """Adds a cached pixel-level representation of an image to the cache
        with the given key.

        Args:
            key: the key of the entry to add
            value: the cached pixel-level representation
            is_static: whether the image is assumed to be static (i.e. the same
                in every frame). Images not marked as static are invalidated
                when Blender changes its current frame.
        """
        self._items[key] = tuple(value)
        if is_static:
            self._dynamic_keys.discard(key)
        else:
            self._dynamic_keys.add(key)

    def clear(self):
        """Clears all cached pixel-level representations of images."""
        self._items.clear()

    def clear_dynamic(self):
        """Removes all cached pixel-level representations of images that are
        not static (i.e. they change when the current frame changes).
        """
        for key in self._dynamic_keys:
            del self._items[key]
        self._dynamic_keys.clear()

    def remove(self, key: str) -> None:
        del self._items[key]
        self._dynamic_keys.discard(key)

    def __getitem__(self, key: str) -> Sequence[float]:
        return self._items[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    # TODO(ntamas): periodical cleanup!
