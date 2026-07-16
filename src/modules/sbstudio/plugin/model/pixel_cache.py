from collections.abc import Iterator, Mapping

from bpy.types import Image
from numpy import empty, float32
from numpy.typing import NDArray

__all__ = ("PixelCache",)


class PixelCache(Mapping[str, NDArray[float32]]):
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

    _items: dict[str, NDArray[float32]]
    """The cached pixels, keyed by the UUIDs of the light effects."""

    _dynamic_keys: set[str]
    """Set of keys that are not static (i.e. they are invalidated when the
    current frame changes).
    """

    def __init__(self):
        """Constructor."""
        self._dynamic_keys = set()
        self._items = {}

    def add(
        self, key: str, value: NDArray[float32], *, is_static: bool = False
    ) -> None:
        """Adds a cached pixel-level representation of an image to the cache
        with the given key.

        Args:
            key: the key of the entry to add
            value: the cached pixel-level representation
            is_static: whether the image is assumed to be static (i.e. the same
                in every frame). Images not marked as static are invalidated
                when Blender changes its current frame.
        """
        self._items[key] = value
        if is_static:
            self._dynamic_keys.discard(key)
        else:
            self._dynamic_keys.add(key)

    def add_image(
        self, key: str, image: Image, *, is_static: bool = False
    ) -> NDArray[float32]:
        """Adds a cached pixel-level representation of an image to the cache
        with the given key.

        Args:
            key: the key of the entry to add
            image: the Blender image to cache
            is_static: whether the image is assumed to be static (i.e. the same
                in every frame). Images not marked as static are invalidated
                when Blender changes its current frame.

        Returns:
            the pixel data of the image in the form it was stored in the cache
        """
        pixel_data = image.pixels
        pixels: NDArray[float32] = empty(len(pixel_data), dtype=float32)
        pixel_data.foreach_get(pixels)
        pixels = pixels.reshape(tuple(image.size) + (-1,))
        self.add(key, pixels, is_static=is_static)
        return pixels

    def clear(self) -> None:
        """Clears all cached pixel-level representations of images."""
        self._items.clear()
        self._dynamic_keys.clear()

    def clear_dynamic(self) -> None:
        """Removes all cached pixel-level representations of images that are
        not static (i.e. they change when the current frame changes).
        """
        for key in self._dynamic_keys:
            self._items.pop(key, None)
        self._dynamic_keys.clear()

    def remove(self, key: str) -> None:
        del self._items[key]
        self._dynamic_keys.discard(key)

    def __getitem__(self, key: str) -> NDArray[float32]:
        return self._items[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    # TODO(ntamas): periodical cleanup!
