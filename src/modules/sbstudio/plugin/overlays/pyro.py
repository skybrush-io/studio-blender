from __future__ import annotations

import blf
import bpy
import gpu

from bpy_extras.view3d_utils import location_3d_to_region_2d
from bpy.types import SpaceView3D
from gpu_extras.batch import batch_for_shader
from typing import TYPE_CHECKING, cast

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

PyroOverlayInfo = tuple[Coordinate3D, list[str]]
"""Type specification for a single info block on the overlay. An info block requires 
a single coordinate and a list of text strings (one per line).
"""

PyroOverlayMarker = tuple[Coordinate3D, Color]
"""Type specification for a single marker on the overlay. A marker requires 
a single coordinate and a Color.
"""

DEFAULT_PYRO_OVERLAY_MARKER_COLOR: Color = (0.5, 0.5, 0.5)
"""Default color for pyro marker overlays."""


class PyroOverlay(ShaderOverlay):
    """Overlay that marks pyro drones in the 3D view."""

    shader_type = "FLAT_COLOR"

    _info_blocks: list[PyroOverlayInfo] | None = None
    _markers: list[PyroOverlayMarker] | None = None
    _shader_batches: list[GPUBatch] | None = None

    @property
    def info_blocks(self) -> list[PyroOverlayInfo] | None:
        return self._info_blocks

    @info_blocks.setter
    def info_blocks(self, value: list[PyroOverlayInfo] | None):
        if value is not None:
            self._info_blocks = []
            for point, lines in value:
                info_block = (
                    tuple(float(c) for c in point),
                    lines,
                )
                self._info_blocks.append(info_block)  # type: ignore

        else:
            self._info_blocks = None

        # self._shader_batches = None

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
        context = bpy.context
        skybrush = getattr(context.scene, "skybrush", None)
        pyro_control: PyroControlPanelProperties | None = getattr(
            skybrush, "pyro_control", None
        )
        if (
            not pyro_control
            or self._info_blocks is None
            or pyro_control.visualization != "INFO"
        ):
            return

        space_data = context.space_data
        if space_data.type != "VIEW_3D":
            return

        space_data = cast(SpaceView3D, space_data)
        if not hasattr(space_data, "overlay") or not bool(
            getattr(space_data.overlay, "show_overlays", False)
        ):
            return

        font_id = 0
        ui_scale = self.get_ui_scale()
        region = context.region
        region_3d = context.region_data
        font_size = int(11 * ui_scale)
        line_height = font_size + 2

        if bpy.app.version >= (4, 0, 0):
            # DPI argument was removed in Blender 4.0
            blf.size(font_id, font_size)
        else:
            blf.size(font_id, font_size, 72)
        blf.enable(font_id, blf.SHADOW)
        blf.color(font_id, 1, 1, 1, 1)

        for info_block in self._info_blocks:
            num_lines = len(info_block[1])
            x, y = location_3d_to_region_2d(region, region_3d, info_block[0])
            y += (num_lines - 3 / 2) * font_size / 2
            for line in info_block[1]:
                blf.position(font_id, x, y, 0)
                blf.draw(font_id, line)
                y -= line_height

    def draw_3d(self) -> None:
        if has_gpu_state_module:
            gpu.state.blend_set("ALPHA")
        else:
            bgl.glEnable(bgl.GL_BLEND)

        skybrush = getattr(bpy.context.scene, "skybrush", None)
        pyro_control: PyroControlPanelProperties | None = getattr(
            skybrush, "pyro_control", None
        )
        if not pyro_control or pyro_control.visualization not in ["MARKERS", "INFO"]:
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
