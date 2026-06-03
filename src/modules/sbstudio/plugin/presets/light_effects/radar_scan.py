from __future__ import annotations

from math import atan2, degrees
from typing import TYPE_CHECKING

from .base import register_preset

if TYPE_CHECKING:
    from sbstudio.model.types import Coordinate3D


RADAR_ANGULAR_SPEED = 2400.0 / 34.0
RADAR_FRAMERATE = 24.0


def _get_plane_coords(position: Coordinate3D, plane: str) -> tuple[float, float]:
    x, y, z = position
    coords = {"X": x, "Y": y, "Z": z}
    a, b = plane.upper()
    return (coords[a], coords[b])


def _radar_scan_core(position, plane: str, fan_angle_deg: float, frame: int) -> float:
    coord_a, coord_b = _get_plane_coords(position, plane)
    time_sec = frame / RADAR_FRAMERATE
    rotation_angle_deg = (time_sec * RADAR_ANGULAR_SPEED) % 360.0
    drone_angle_deg = degrees(atan2(coord_b, coord_a))
    if drone_angle_deg < 0:
        drone_angle_deg += 360.0
    fan_start = rotation_angle_deg
    fan_end = (rotation_angle_deg + fan_angle_deg) % 360.0
    if fan_start <= fan_end:
        in_fan = fan_start <= drone_angle_deg <= fan_end
    else:
        in_fan = (drone_angle_deg >= fan_start) or (drone_angle_deg <= fan_end)
    return 1.0 if in_fan else 0.0


@register_preset(
    id="radar_scan_60_xy",
    label="Radar Scan 60° XY",
    translations=(("zh", "雷达扫描 60度 XY"), ("ja", "レーダースキャン 60° XY")),
)
def radar_scan_60_xy(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _radar_scan_core(position, "XY", 60.0, frame)


@register_preset(
    id="radar_scan_90_xy",
    label="Radar Scan 90° XY",
    translations=(("zh", "雷达扫描 90度 XY"), ("ja", "レーダースキャン 90° XY")),
)
def radar_scan_90_xy(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _radar_scan_core(position, "XY", 90.0, frame)


@register_preset(
    id="radar_scan_120_xy",
    label="Radar Scan 120° XY",
    translations=(("zh", "雷达扫描 120度 XY"), ("ja", "レーダースキャン 120° XY")),
)
def radar_scan_120_xy(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _radar_scan_core(position, "XY", 120.0, frame)


@register_preset(
    id="radar_scan_60_xz",
    label="Radar Scan 60° XZ",
    translations=(("zh", "雷达扫描 60度 XZ"), ("ja", "レーダースキャン 60° XZ")),
)
def radar_scan_60_xz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _radar_scan_core(position, "XZ", 60.0, frame)


@register_preset(
    id="radar_scan_90_xz",
    label="Radar Scan 90° XZ",
    translations=(("zh", "雷达扫描 90度 XZ"), ("ja", "レーダースキャン 90° XZ")),
)
def radar_scan_90_xz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _radar_scan_core(position, "XZ", 90.0, frame)


@register_preset(
    id="radar_scan_120_xz",
    label="Radar Scan 120° XZ",
    translations=(("zh", "雷达扫描 120度 XZ"), ("ja", "レーダースキャン 120° XZ")),
)
def radar_scan_120_xz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _radar_scan_core(position, "XZ", 120.0, frame)


@register_preset(
    id="radar_scan_60_yz",
    label="Radar Scan 60° YZ",
    translations=(("zh", "雷达扫描 60度 YZ"), ("ja", "レーダースキャン 60° YZ")),
)
def radar_scan_60_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _radar_scan_core(position, "YZ", 60.0, frame)


@register_preset(
    id="radar_scan_90_yz",
    label="Radar Scan 90° YZ",
    translations=(("zh", "雷达扫描 90度 YZ"), ("ja", "レーダースキャン 90° YZ")),
)
def radar_scan_90_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _radar_scan_core(position, "YZ", 90.0, frame)


@register_preset(
    id="radar_scan_120_yz",
    label="Radar Scan 120° YZ",
    translations=(("zh", "雷达扫描 120度 YZ"), ("ja", "レーダースキャン 120° YZ")),
)
def radar_scan_120_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _radar_scan_core(position, "YZ", 120.0, frame)


# Global parameters for v5.1 effects
PAINT_DURATION_FRAMES = 120
PAINT_FRAMERATE = 24.0


# Helper functions for v5.1 effects
def _v51_paint_on_core(position: Coordinate3D, plane: str, frame: int) -> float:
    coord_a, coord_b = _get_plane_coords(position, plane)
    drone_angle_deg = degrees(atan2(coord_b, coord_a))
    if drone_angle_deg < 0:
        drone_angle_deg += 360.0
    phase = min(frame / max(PAINT_DURATION_FRAMES, 1), 1.0)
    current_angle_deg = phase * 360.0
    if drone_angle_deg <= current_angle_deg:
        return 1.0
    else:
        return 0.0


@register_preset(
    id="pattern_paint_on_xy",
    label="Pattern Paint-On XY",
    translations=(("zh", "图案逐渐点亮 XY"), ("ja", "パターンペイント XY")),
)
def pattern_paint_on_xy(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _v51_paint_on_core(position, "XY", frame)
