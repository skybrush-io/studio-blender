from __future__ import annotations

import bpy
import gpu

from gpu_extras.batch import batch_for_shader
from typing import TYPE_CHECKING

from sbstudio.model.types import Coordinate3D

from .base import ShaderOverlay

if TYPE_CHECKING:
    from sbstudio.plugin.model.pyro_control import PyroControlPanelProperties
    from gpu.types import GPUBatch

try:
    import gpu.state

    has_gpu_state_module = True
except ImportError:
    import bgl

    has_gpu_state_module = False

__all__ = (
    "PyroOverlay",
    "PyroOverlayMarker",
)

Color = tuple[float, float, float]
"""Type alias for RGB colors in this module."""

PyroOverlayMarker = tuple[Coordinate3D, Color]
"""Type specification for a single marker on the overlay. A marker requires 
a single coordinate and a Color.
"""

DEFAULT_PYRO_OVERLAY_MARKER_COLOR: Color = (0.5, 0.5, 0.5)
"""Default color for pyro marker overlays."""


class PyroOverlay(ShaderOverlay):
    """Overlay that marks the closest pair of drones and all drones above the
    altitude threshold in the 3D view.
    """

    shader_type = "FLAT_COLOR"

    _markers: list[PyroOverlayMarker] | None = None
    _shader_batches: list[GPUBatch] | None = None

    @property
    def markers(self) -> list[PyroOverlayMarker] | None:
        return self._markers

    @markers.setter
    def markers(self, value: list[PyroOverlayMarker] | None):
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

    def draw_2d(self) -> None:
        return

    def draw_3d(self) -> None:
        if has_gpu_state_module:
            gpu.state.blend_set("ALPHA")
        else:
            bgl.glEnable(bgl.GL_BLEND)

        skybrush = getattr(bpy.context.scene, "skybrush", None)
        pyro_control: PyroControlPanelProperties | None = getattr(
            skybrush, "pyro_control", None
        )
        if not pyro_control or pyro_control.visualization != "MARKERS":
            return

        if self._markers is not None:
            assert self._shader is not None

            if self._shader_batches is None:
                self._shader_batches = self._create_shader_batches()

            if self._shader_batches:
                self._shader.bind()
                if has_gpu_state_module:
                    gpu.state.point_size_set(30)
                else:
                    bgl.glPointSize(30)
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
