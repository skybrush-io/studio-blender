from __future__ import annotations

from typing import TYPE_CHECKING

import bpy
import gpu
import gpu.state
from gpu_extras.batch import batch_for_shader

from sbstudio.model.types import Coordinate3D, RGBColor

from .base import ShaderOverlay

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


class LightEffectOverlay(ShaderOverlay):
    """Overlay that marks light effect colors of drones in the 3D view."""

    shader_type = "POINT_FLAT_COLOR"

    _markers: list[LightEffectOverlayMarker] | None = None
    _shader_batches: list[GPUBatch] | None = None

    @property
    def markers(self) -> list[LightEffectOverlayMarker] | None:
        return self._markers

    @markers.setter
    def markers(self, value: list[LightEffectOverlayMarker] | None):
        if value is not None:
            self._markers = []
            for point, color in value:
                marker = (
                    tuple(float(c) for c in point),
                    tuple(float(c) for c in color),
                )
                self._markers.append(marker)  # type: ignore

        else:
            self._markers = None

        self._shader_batches = None

    def draw_3d(self) -> None:
        gpu.state.blend_set("ALPHA")

        skybrush = getattr(bpy.context.scene, "skybrush", None)
        light_effects: LightEffectCollection | None = getattr(
            skybrush, "light_effects", None
        )
        if not light_effects or light_effects.visualization != "MARKERS":
            return

        if self._markers is not None:
            assert self._shader is not None

            if self._shader_batches is None:
                self._shader_batches = self._create_shader_batches()

            if self._shader_batches:
                self._shader.bind()
                gpu.state.point_size_set(25)
                for batch in self._shader_batches:
                    batch.draw(self._shader)

    def dispose(self) -> None:
        super().dispose()
        self._shader_batches = None

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
