from __future__ import annotations

from typing import TYPE_CHECKING

import bpy
import gpu.state
from gpu_extras.batch import batch_for_shader

from sbstudio.model.types import Coordinate3D, RGBColor

from .base import ShaderBatchBasedOverlay

if TYPE_CHECKING:
    from gpu.types import GPUBatch

    from sbstudio.plugin.model.light_effects import LightEffectCollection

__all__ = (
    "LightEffectOverlay",
    "LightEffectOverlayMarker",
)

LightEffectOverlayMarker = tuple[Coordinate3D, RGBColor]
"""Type specification for a single marker on the overlay. A marker requires
a single coordinate and a Color.
"""


class LightEffectOverlay(ShaderBatchBasedOverlay):
    """Overlay that marks light effect colors of drones in the 3D view."""

    shader_type = "POINT_FLAT_COLOR"

    _markers: list[LightEffectOverlayMarker] | None = None

    @property
    def markers(self) -> list[LightEffectOverlayMarker] | None:
        return self._markers

    @markers.setter
    def markers(self, value: list[LightEffectOverlayMarker] | None):
        if value is not None:
            self._markers = []
            for point, color in value:
                marker = (
                    (float(point[0]), float(point[1]), float(point[2])),
                    (float(color[0]), float(color[1]), float(color[2])),
                )
                self._markers.append(marker)
        else:
            self._markers = None

        self.invalidate_shader_batches()

    def draw_3d(self) -> None:
        skybrush = getattr(bpy.context.scene, "skybrush", None)
        light_effects: LightEffectCollection | None = getattr(
            skybrush, "light_effects", None
        )
        if not light_effects:
            return

        if self._markers is not None:
            self._draw_shader_batches()

    def _create_shader_batches(self) -> list[GPUBatch]:
        assert self._shader is not None

        points: list[Coordinate3D] = []
        colors: list[tuple[float, ...]] = []

        for point, color in self._markers or ():
            points.append(point)
            colors.append(color)

        # Construct the shader batch to draw the lines on the UI
        batches: list[GPUBatch] = [
            batch_for_shader(self._shader, "POINTS", {"pos": points, "color": colors}),
        ]

        return batches

    def _prepare_gpu_state(self) -> None:
        gpu.state.point_size_set(25)
