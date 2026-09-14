from enum import IntEnum, auto

from numpy import float32, maximum, minimum, where
from numpy.typing import NDArray

__all__ = ("blend_in_place", "BlendMode")


class BlendMode(IntEnum):
    NORMAL = auto()
    MULTIPLY = auto()
    SCREEN = auto()
    DARKEN = auto()
    LIGHTEN = auto()
    OVERLAY = auto()
    SOFT_LIGHT = auto()
    HARD_LIGHT = auto()

    # Do not change the order of items above to remain compatible with already
    # saved Blender scenes.

    @property
    def description(self) -> str:
        return self.name.lower().replace("_", " ").capitalize()


def blend_in_place(
    source: NDArray[float32],
    backdrop: NDArray[float32],
    mode: BlendMode = BlendMode.NORMAL,
) -> None:
    """Blends two color arrays according to standard alpha compositing rules,
    using the given blending mode and updating the backdrop array in-place.

    Operates on multiple RGBA colors at once.

    Args:
        source: Source colors, shape ``(n, 4)``, RGBA each in ``[0, 1]``.
        backdrop: Backdrop colors, shape ``(n, 4)``, modified in-place.
        mode: The blending mode to use. Defaults to ``BlendMode.NORMAL``.
    """
    alpha_source = source[:, 3]
    mask_active = alpha_source > 0
    if not mask_active.any():
        # Shortcut for fully transparent sources
        return

    if mode is BlendMode.NORMAL:
        # Shortcut for the common case when the source is opaque and the
        # mode is NORMAL. Applied only for those rows where the source is fully opaque;
        # the procedure continues with the remaining rows later.
        mask_opaque = alpha_source >= 1
        backdrop[mask_opaque] = source[mask_opaque]
        mask_active &= ~mask_opaque
        if not mask_active.any():
            return

    source = source[mask_active]
    work = backdrop[mask_active]

    alpha_source = source[:, 3]
    alpha_backdrop = work[:, 3]

    alpha_overlay = where(
        alpha_backdrop >= 1,
        1.0,
        1.0 - (1.0 - alpha_source) * (1.0 - alpha_backdrop),
    )
    a = where(alpha_backdrop >= 1, alpha_source, alpha_source / alpha_overlay)[:, None]

    source_rgb = source[:, :3]
    backdrop_rgb = work[:, :3]
    a3 = a * source_rgb
    b3 = (1.0 - a) * backdrop_rgb

    match mode:
        case BlendMode.NORMAL:
            work[:, :3] = a3 + b3
        case BlendMode.MULTIPLY:
            work[:, :3] = a3 * backdrop_rgb + b3
        case BlendMode.SCREEN:
            work[:, :3] = a * (1.0 - (1.0 - backdrop_rgb) * (1.0 - source_rgb)) + b3
        case BlendMode.DARKEN:
            work[:, :3] = a * minimum(backdrop_rgb, source_rgb) + b3
        case BlendMode.LIGHTEN:
            work[:, :3] = a * maximum(backdrop_rgb, source_rgb) + b3
        case BlendMode.OVERLAY:
            mask = backdrop_rgb >= 0.5
            work[:, :3] = where(
                mask,
                a * (1.0 - (2.0 - 2.0 * backdrop_rgb) * (1.0 - source_rgb)) + b3,
                a * (2.0 * backdrop_rgb) * source_rgb + b3,
            )
        case BlendMode.HARD_LIGHT:
            mask = source_rgb <= 0.5
            work[:, :3] = where(
                mask,
                a * backdrop_rgb * (2.0 * source_rgb) + b3,
                a * (1.0 - (1.0 - backdrop_rgb) * (2.0 - 2.0 * source_rgb)) + b3,
            )
        case BlendMode.SOFT_LIGHT:
            mask_src = source_rgb <= 0.5
            result_le = backdrop_rgb - (1.0 - 2.0 * source_rgb) * backdrop_rgb * (
                1.0 - backdrop_rgb
            )
            mask_bd = backdrop_rgb <= 0.25
            d_val = where(
                mask_bd,
                ((16.0 * backdrop_rgb - 12.0) * backdrop_rgb + 4.0) * backdrop_rgb,
                backdrop_rgb**0.5,
            )
            result_gt = backdrop_rgb + (2.0 * source_rgb - 1.0) * (d_val - backdrop_rgb)
            result = where(mask_src, result_le, result_gt)
            work[:, :3] = a * result + b3

    work[:, 3] = alpha_overlay
    backdrop[mask_active] = work
