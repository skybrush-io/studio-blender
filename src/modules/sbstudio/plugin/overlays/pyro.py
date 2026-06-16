from __future__ import annotations

from typing import TYPE_CHECKING, Sequence, cast

import blf
import bpy
import gpu.state
from bpy.types import SpaceView3D
from bpy_extras.view3d_utils import location_3d_to_region_2d
from gpu_extras.batch import batch_for_shader

from sbstudio.model.types import Coordinate3D, RGBColor

from .base import ShaderBatchBasedOverlay

if TYPE_CHECKING:
    from gpu.types import GPUBatch

    from sbstudio.plugin.model.pyro_control import PyroControlPanelProperties

__all__ = (
    "PyroOverlay",
    "PyroOverlayMarker",
)

PyroOverlayInfo = tuple[Coordinate3D, list[str]]
"""Type specification for a single info block on the overlay. An info block requires
a single coordinate and a list of text strings (one per line).
"""

PyroOverlayMarker = tuple[Coordinate3D, RGBColor]
"""Type specification for a single marker on the overlay. A marker requires
a single coordinate and a Color.
"""

DEFAULT_PYRO_OVERLAY_MARKER_COLOR: RGBColor = (0.5, 0.5, 0.5)
"""Default color for pyro marker overlays."""


class PyroOverlay(ShaderBatchBasedOverlay):
    """Overlay that marks pyro drones in the 3D view."""

    shader_type = "POINT_FLAT_COLOR"

    _info_blocks: list[PyroOverlayInfo] | None = None
    _markers: list[PyroOverlayMarker] | None = None

    @property
    def info_blocks(self) -> list[PyroOverlayInfo] | None:
        return self._info_blocks

    @info_blocks.setter
    def info_blocks(self, value: list[PyroOverlayInfo] | None):
        if value is not None:
            self._info_blocks = []
            for point, lines in value:
                info_block = (
                    (float(point[0]), float(point[1]), float(point[2])),
                    lines,
                )
                self._info_blocks.append(info_block)

        else:
            self._info_blocks = None

        # self.invalidate_shader_batches()

    @property
    def markers(self) -> Sequence[PyroOverlayMarker] | None:
        return self._markers

    @markers.setter
    def markers(self, value: Sequence[PyroOverlayMarker] | None):
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

    @property
    def marker_size(self):
        context = bpy.context
        skybrush = getattr(context.scene, "skybrush", None)
        pyro_control: PyroControlPanelProperties | None = getattr(
            skybrush, "pyro_control", None
        )
        return pyro_control.marker_size if pyro_control is not None else 20

    def draw_2d(self) -> None:
        context = bpy.context
        skybrush = getattr(context.scene, "skybrush", None)
        pyro_control: PyroControlPanelProperties | None = getattr(
            skybrush, "pyro_control", None
        )
        if not pyro_control or not self._info_blocks:
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

        blf.size(font_id, font_size)
        blf.enable(font_id, blf.SHADOW)
        blf.color(font_id, 1, 1, 1, 1)

        for info_block in self._info_blocks:
            num_lines = len(info_block[1])
            vec = location_3d_to_region_2d(region, region_3d, info_block[0])
            if vec is None:
                continue

            x, y = vec
            y += (num_lines - 3 / 2) * font_size / 2
            for line in info_block[1]:
                blf.position(font_id, x, y, 0)
                blf.draw(font_id, line)
                y -= line_height

    def should_draw(self) -> bool:
        skybrush = getattr(bpy.context.scene, "skybrush", None)
        pyro_control: PyroControlPanelProperties | None = getattr(
            skybrush, "pyro_control", None
        )
        return pyro_control is not None and pyro_control.visualization in (
            "MARKERS",
            "INFO",
        )

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
        gpu.state.point_size_set(self.marker_size)
