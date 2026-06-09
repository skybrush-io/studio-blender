from __future__ import annotations

from math import cos, sin
from typing import TYPE_CHECKING

from .base import register_preset

if TYPE_CHECKING:
    from sbstudio.model.types import Coordinate3D

CHASE_SPEED = 0.12
CHASE_SPATIAL_K = 0.1


def _chasing_tails_core(
    position: Coordinate3D, axis: int, frame: int, formation_index: int | None
) -> float:
    coord = position[axis]
    fi = formation_index if formation_index is not None else 0
    travel_phase = frame * CHASE_SPEED - coord * CHASE_SPATIAL_K
    v = cos(travel_phase) if fi % 2 else sin(travel_phase)
    return (v + 1) / 2


@register_preset(
    id="chasing_tails_x",
    label="Chasing Tails X",
    translations=(("zh", "追逐尾巴 X"), ("ja", "追跡 X")),
)
def chasing_tails_x(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _chasing_tails_core(position, 0, frame, formation_index)


@register_preset(
    id="chasing_tails_y",
    label="Chasing Tails Y",
    translations=(("zh", "追逐尾巴 Y"), ("ja", "追跡 Y")),
)
def chasing_tails_y(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _chasing_tails_core(position, 1, frame, formation_index)


@register_preset(
    id="chasing_tails_z",
    label="Chasing Tails Z",
    translations=(("zh", "追逐尾巴 Z"), ("ja", "追跡 Z")),
)
def chasing_tails_z(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _chasing_tails_core(position, 2, frame, formation_index)
