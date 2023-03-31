import blf
import bpy
import gpu

from gpu_extras.batch import batch_for_shader
from typing import Any, List, Optional, Sequence

from sbstudio.model.types import Coordinate3D

from .base import ShaderOverlay

try:
    import gpu.state

    has_gpu_state_module = True
except ImportError:
    import bgl

    has_gpu_state_module = False

__all__ = ("SafetyCheckOverlay",)

#: Type specification for markers on the overlay. Each marker is a sequence of
#: coordinates that are interconnected with lines.
MarkerList = List[Sequence[Coordinate3D]]


def set_warning_color_iff(condition: bool, font_id: int) -> None:
    if condition:
        blf.color(font_id, 1, 1, 0, 1)
    else:
        blf.color(font_id, 1, 1, 1, 1)


class SafetyCheckOverlay(ShaderOverlay):
    """Overlay that marks the closest pair of drones and all drones above the
    altitude threshold in the 3D view.
    """

    _markers: Optional[MarkerList] = None
    _shader_batches: Any

    def __init__(self):
        super().__init__()

        self._shader_batches = None

    @property
    def markers(self) -> Optional[MarkerList]:
        return self._markers

    @markers.setter
    def markers(self, value):
        if value is not None:
            self._markers = []
            for marker_points in value:
                marker_points = tuple(
                    tuple(float(coord) for coord in point) for point in marker_points
                )
                self._markers.append(marker_points)

        else:
            self._markers = None

        self._shader_batches = None

    def draw_2d(self) -> None:
        skybrush = getattr(bpy.context.scene, "skybrush", None)
        safety_check = getattr(skybrush, "safety_check", None)
        if not safety_check:
            return

        font_id = 0

        context = bpy.context
        space_data = context.space_data
        if not hasattr(space_data, "overlay") or not bool(
            getattr(space_data.overlay, "show_overlays", False)
        ):
            return

        left_panel_width = context.area.regions[2].width
        total_height = context.area.height

        ui_scale = self.get_ui_scale()

        # Margin width was changed between Blender 2.83 and Blender 2.90
        if bpy.app.version < (2, 90):
            left_margin = left_panel_width + 19 * ui_scale
        else:
            left_margin = left_panel_width + 10 * ui_scale

        y = total_height - 72 * ui_scale
        if hasattr(space_data, "overlay"):
            if getattr(space_data.overlay, "show_text", False):
                y -= 36 * ui_scale
            if getattr(space_data.overlay, "show_stats", False):
                y -= 112 * ui_scale

        line_height = 18 * ui_scale

        blf.size(font_id, int(11 * ui_scale), 72)
        blf.enable(font_id, blf.SHADOW)

        blf.color(font_id, 1, 1, 1, 1)
        blf.position(font_id, left_margin, y, 0)
        blf.draw(font_id, safety_check.formation_status)
        y -= line_height

        if (
            safety_check.proximity_warning_enabled
            and safety_check.min_distance_is_valid
        ):
            set_warning_color_iff(safety_check.should_show_proximity_warning, font_id)
            blf.position(font_id, left_margin, y, 0)
            blf.draw(font_id, f"Min distance: {safety_check.min_distance:.1f} m")
            y -= line_height

        if safety_check.altitude_warning_enabled and safety_check.max_altitude_is_valid:
            set_warning_color_iff(safety_check.should_show_altitude_warning, font_id)
            blf.position(font_id, left_margin, y, 0)
            blf.draw(
                font_id,
                f"Altitude: {safety_check.min_altitude:.1f} - {safety_check.max_altitude:.1f} m",
            )
            y -= line_height

        if (
            safety_check.velocity_warning_enabled
            and safety_check.max_velocities_are_valid
        ):
            set_warning_color_iff(safety_check.should_show_velocity_warning, font_id)
            blf.position(font_id, left_margin, y, 0)
            blf.draw(
                font_id,
                f"Max velocity XY: {safety_check.max_velocity_xy:.1f} m/s | "
                f"U: {safety_check.max_velocity_z_up:.1f} m/s | "
                f"D: {safety_check.max_velocity_z_down:.1f} m/s",
            )
            y -= line_height

    def draw_3d(self) -> None:
        if has_gpu_state_module:
            gpu.state.blend_set("ALPHA")
        else:
            bgl.glEnable(bgl.GL_BLEND)

        if self._markers is not None:
            if self._shader_batches is None:
                self._shader_batches = self._create_shader_batches()

            if self._shader_batches:
                self._shader.bind()
                self._shader.uniform_float("color", (1, 0, 0, 1))
                if has_gpu_state_module:
                    gpu.state.line_width_set(5)
                    gpu.state.point_size_set(20)
                else:
                    bgl.glLineWidth(5)
                    bgl.glPointSize(20)
                for batch in self._shader_batches:
                    batch.draw(self._shader)

    def dispose(self) -> None:
        super().dispose()
        self._shader_batches = None

    def _create_shader_batches(self):
        batches, points, lines = [], [], []

        for marker_points in self._markers or ():
            points.extend(marker_points)

            if marker_points:
                if len(marker_points) > 2:
                    prev = points[-1]
                    for curr in marker_points:
                        lines.extend((prev, curr))
                        prev = curr
                elif len(marker_points) == 2:
                    lines.extend(marker_points)

        # Construct the shader batch to draw the lines on the UI
        batches.extend(
            [
                batch_for_shader(self._shader, "LINES", {"pos": lines}),
                batch_for_shader(self._shader, "POINTS", {"pos": points}),
            ]
        )

        return batches
