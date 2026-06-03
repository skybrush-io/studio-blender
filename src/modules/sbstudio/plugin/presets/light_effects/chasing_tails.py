from __future__ import annotations

from math import cos, sin
from typing import TYPE_CHECKING

from .base import register_preset

if TYPE_CHECKING:
    from sbstudio.model.types import Coordinate3D

CHASE_SPEED = 0.12
CHASE_SPATIAL_K = 0.1


def _chasing_tails_core(position, plane: str, frame: int, formation_index) -> float:
    if position is None:
        coord = 0.0
    else:
        axis = plane[0].upper()
        coords_map = {"X": position[0], "Y": position[1], "Z": position[2]}
        coord = coords_map[axis]
    fi = formation_index if formation_index is not None else 0
    group = fi % 2
    travel_phase = frame * CHASE_SPEED - coord * CHASE_SPATIAL_K
    if group == 0:
        v = sin(travel_phase)
    else:
        v = cos(travel_phase)
    return (v + 1) / 2


@register_preset(
    id="chasing_tails_xy",
    label="Chasing Tails XY",
    translations=(("zh", "追逐尾巴 XY"), ("ja", "追跡 XY")),
)
def chasing_tails_xy(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _chasing_tails_core(position, "XY", frame, formation_index)


@register_preset(
    id="chasing_tails_xz",
    label="Chasing Tails XZ",
    translations=(("zh", "追逐尾巴 XZ"), ("ja", "追跡 XZ")),
)
def chasing_tails_xz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _chasing_tails_core(position, "XZ", frame, formation_index)


@register_preset(
    id="chasing_tails_yz",
    label="Chasing Tails YZ",
    translations=(("zh", "追逐尾巴 YZ"), ("ja", "追跡 YZ")),
)
def chasing_tails_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _chasing_tails_core(position, "YZ", frame, formation_index)
