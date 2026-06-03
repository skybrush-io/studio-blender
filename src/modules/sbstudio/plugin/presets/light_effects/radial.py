from __future__ import annotations

from math import hypot, sin
from typing import TYPE_CHECKING

from .base import register_preset

if TYPE_CHECKING:
    from sbstudio.model.types import Coordinate3D

RADIAL_SPEED = 0.10
RADIAL_WAVE_K = 0.30


def _get_projected_plane_distance(position: Coordinate3D, plane: str) -> float:
    x, y, z = position
    coords = {"X": x, "Y": y, "Z": z}
    a, b = plane.upper()
    return hypot(coords[a], coords[b])


# 1. Radial Diffusion (径向扩散) - 3 presets
@register_preset(
    id="radial_diffusion_xy",
    label="Radial Diffusion XY",
    translations=(("zh", "径向扩散 XY"), ("ja", "放射拡散 XY")),
)
def radial_diffusion_xy(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    distance = _get_projected_plane_distance(position, "XY")
    return (sin(frame * RADIAL_SPEED - distance * RADIAL_WAVE_K) + 1) / 2


@register_preset(
    id="radial_diffusion_xz",
    label="Radial Diffusion XZ",
    translations=(("zh", "径向扩散 XZ"), ("ja", "放射拡散 XZ")),
)
def radial_diffusion_xz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    distance = _get_projected_plane_distance(position, "XZ")
    return (sin(frame * RADIAL_SPEED - distance * RADIAL_WAVE_K) + 1) / 2


@register_preset(
    id="radial_diffusion_yz",
    label="Radial Diffusion YZ",
    translations=(("zh", "径向扩散 YZ"), ("ja", "放射拡散 YZ")),
)
def radial_diffusion_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    distance = _get_projected_plane_distance(position, "YZ")
    return (sin(frame * RADIAL_SPEED - distance * RADIAL_WAVE_K) + 1) / 2


# 2. Radial Convergence (径向汇聚) - 3 presets
@register_preset(
    id="radial_convergence_xy",
    label="Radial Convergence XY",
    translations=(("zh", "径向汇聚 XY"), ("ja", "放射収束 XY")),
)
def radial_convergence_xy(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    distance = _get_projected_plane_distance(position, "XY")
    return (sin(frame * RADIAL_SPEED + distance * RADIAL_WAVE_K) + 1) / 2


@register_preset(
    id="radial_convergence_xz",
    label="Radial Convergence XZ",
    translations=(("zh", "径向汇聚 XZ"), ("ja", "放射収束 XZ")),
)
def radial_convergence_xz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    distance = _get_projected_plane_distance(position, "XZ")
    return (sin(frame * RADIAL_SPEED + distance * RADIAL_WAVE_K) + 1) / 2


@register_preset(
    id="radial_convergence_yz",
    label="Radial Convergence YZ",
    translations=(("zh", "径向汇聚 YZ"), ("ja", "放射収束 YZ")),
)
def radial_convergence_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    distance = _get_projected_plane_distance(position, "YZ")
    return (sin(frame * RADIAL_SPEED + distance * RADIAL_WAVE_K) + 1) / 2
