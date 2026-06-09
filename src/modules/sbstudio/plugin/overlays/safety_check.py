from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, cast

import blf
import bpy
import gpu.state
from bpy.types import SpaceView3D
from gpu_extras.batch import batch_for_shader

from sbstudio.model.types import Coordinate3D, RGBColor
from sbstudio.plugin.model.safety_check import SafetyCheckProperties

from .base import ShaderBatchBasedOverlay

if TYPE_CHECKING:
    from gpu.types import GPUBatch


__all__ = ("SafetyCheckOverlay",)

MarkerGroup = Literal[
    "altitude", "proximity", "velocity", "acceleration", "yaw", "generic"
]
"""Currently supported marker groups."""

Marker = tuple[Sequence[Coordinate3D], MarkerGroup]
"""Type specification for a single marker on the overlay. A marker is a sequence
of coordinates that are interconnected with lines and have an optional
group name. Markers in the same group are colored with the same color.
"""

ALTITUDE_WARNING_COLOR: RGBColor = (0.47, 0.65, 1.0)  # "Blender blue"
GENERIC_WARNING_COLOR: RGBColor = (1, 0, 0)  # red
PROXIMITY_WARNING_COLOR: RGBColor = (1, 0, 0)  # red
VELOCITY_WARNING_COLOR: RGBColor = (1, 1, 0)  # yellow
ACCELERATION_WARNING_COLOR: RGBColor = (1, 0, 1)  # magenta
YAW_WARNING_COLOR: RGBColor = (0, 1, 1)  # light blue

_group_to_color_map: dict[str, RGBColor] = {
    "generic": GENERIC_WARNING_COLOR,
    "altitude": ALTITUDE_WARNING_COLOR,
    "proximity": PROXIMITY_WARNING_COLOR,
    "velocity": VELOCITY_WARNING_COLOR,
    "acceleration": ACCELERATION_WARNING_COLOR,
    "yaw": YAW_WARNING_COLOR,
}
"""Mapping from marker group names to the corresponding colors on the overlay."""


def set_warning_color_iff(
    condition: bool, font_id: int, color: tuple[float, float, float]
) -> None:
    if condition:
        blf.color(font_id, *color, 1)
    else:
        blf.color(font_id, 1, 1, 1, 1)


class SafetyCheckOverlay(ShaderBatchBasedOverlay):
    """Overlay that marks the closest pair of drones and all drones above the
    altitude threshold in the 3D view.
    """

    shader_type = "POINT_FLAT_COLOR"

    _markers: list[Marker] | None = None

    @property
    def markers(self) -> Sequence[Marker] | None:
        return self._markers

    @markers.setter
    def markers(self, value: Sequence[Marker] | None):
        if value is not None:
            self._markers = []
            for marker_points, group in value:
                marker_points = tuple(
                    (float(point[0]), float(point[1]), float(point[2]))
                    for point in marker_points
                )
                self._markers.append((marker_points, group))
        else:
            self._markers = None

        self.invalidate_shader_batches()

    def draw_2d(self) -> None:
        skybrush = getattr(bpy.context.scene, "skybrush", None)
        safety_check: SafetyCheckProperties | None = getattr(
            skybrush, "safety_check", None
        )
        if not safety_check:
            return

        font_id = 0

        context = bpy.context
        space_data = context.space_data
        if space_data.type != "VIEW_3D":
            return

        space_data = cast(SpaceView3D, space_data)
        if not hasattr(space_data, "overlay") or not bool(
            getattr(space_data.overlay, "show_overlays", False)
        ):
            return

        left_panel_width = context.area.regions[4].width
        total_height = context.area.height

        ui_scale = self.get_ui_scale()

        left_margin = left_panel_width + 10 * ui_scale

        y = total_height - 72 * ui_scale
        if space_data.type == "VIEW_3D":
            if getattr(space_data.overlay, "show_text", False):
                y -= 36 * ui_scale
            if getattr(space_data.overlay, "show_stats", False):
                y -= 112 * ui_scale

        line_height = 18 * ui_scale

        blf.size(font_id, int(11 * ui_scale))
        blf.enable(font_id, blf.SHADOW)

        blf.color(font_id, 1, 1, 1, 1)
        blf.position(font_id, left_margin, y, 0)
        blf.draw(font_id, safety_check.formation_status)
        y -= line_height

        if (
            safety_check.proximity_warning_enabled
            and safety_check.min_distance_is_valid
        ):
            set_warning_color_iff(
                safety_check.should_show_proximity_warning,
                font_id,
                PROXIMITY_WARNING_COLOR,
            )
            blf.position(font_id, left_margin, y, 0)
            blf.draw(font_id, f"Min distance: {safety_check.min_distance:.2f} m")
            y -= line_height

        if safety_check.altitude_warning_enabled and safety_check.max_altitude_is_valid:
            set_warning_color_iff(
                safety_check.should_show_altitude_warning,
                font_id,
                ALTITUDE_WARNING_COLOR,
            )
            blf.position(font_id, left_margin, y, 0)
            blf.draw(
                font_id,
                f"Altitude: {safety_check.min_altitude:.2f} - {safety_check.max_altitude:.2f} m",
            )
            y -= line_height

        if (
            safety_check.velocity_warning_enabled
            and safety_check.max_velocities_are_valid
        ):
            set_warning_color_iff(
                safety_check.should_show_velocity_warning,
                font_id,
                VELOCITY_WARNING_COLOR,
            )
            blf.position(font_id, left_margin, y, 0)
            blf.draw(
                font_id,
                f"Max velocity XY: {safety_check.max_velocity_xy:.1f} m/s | "
                f"U: {safety_check.max_velocity_z_up:.1f} m/s | "
                f"D: {safety_check.max_velocity_z_down:.1f} m/s",
            )
            y -= line_height

        if (
            safety_check.acceleration_warning_enabled
            and safety_check.max_acceleration_is_valid
        ):
            set_warning_color_iff(
                safety_check.should_show_acceleration_warning,
                font_id,
                ACCELERATION_WARNING_COLOR,
            )
            blf.position(font_id, left_margin, y, 0)
            blf.draw(
                font_id, f"Max acceleration: {safety_check.max_acceleration:.1f} m/s/s"
            )
            y -= line_height

        if safety_check.yaw_rate_warning_enabled and safety_check.max_yaw_rate_is_valid:
            set_warning_color_iff(
                safety_check.should_show_yaw_rate_warning,
                font_id,
                YAW_WARNING_COLOR,
            )
            blf.position(font_id, left_margin, y, 0)
            blf.draw(font_id, f"Max yaw rate: {safety_check.max_yaw_rate:.1f} deg/s")
            y -= line_height

    def _create_shader_batches(self) -> list[GPUBatch]:
        assert self._shader is not None

        batches: list[GPUBatch] = []
        points: list[Coordinate3D] = []
        lines: list[Coordinate3D] = []
        point_colors: list[tuple[float, ...]] = []
        line_colors: list[tuple[float, ...]] = []

        RED = _group_to_color_map["generic"]

        for marker_points, group in self._markers or ():
            color = _group_to_color_map.get(group, RED)
            points.extend(marker_points)
            point_colors.extend([color] * len(marker_points))

            if marker_points:
                if len(marker_points) > 2:
                    prev = points[-1]
                    for curr in marker_points:
                        lines.extend((prev, curr))
                        prev = curr
                    line_colors.extend([color] * len(marker_points))
                elif len(marker_points) == 2:
                    lines.extend(marker_points)
                    line_colors.extend([color, color])

        # Construct the shader batches to draw the lines on the UI
        if lines:
            batches.append(
                batch_for_shader(
                    self._shader, "LINES", {"pos": lines, "color": line_colors}
                )
            )
        if points:
            batches.append(
                batch_for_shader(
                    self._shader, "POINTS", {"pos": points, "color": point_colors}
                )
            )

        return batches

    def _prepare_gpu_state(self) -> None:
        gpu.state.point_size_set(30)
        gpu.state.line_width_set(5)
