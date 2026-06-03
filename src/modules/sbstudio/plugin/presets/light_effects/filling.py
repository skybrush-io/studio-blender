from __future__ import annotations

from math import pi, sin
from typing import TYPE_CHECKING

from .base import register_preset

if TYPE_CHECKING:
    from sbstudio.model.types import Coordinate3D


def _continuous_filling(
    frame, formation_index, drone_count, speed_factor, divisor
) -> float:
    if not drone_count:
        return 0.0
    wave_length = max(drone_count / divisor, 1e-6)
    fi = formation_index or 0
    offset = (fi % wave_length) / wave_length
    return (sin((frame * 0.1 * speed_factor) + offset * 2 * pi) + 1) / 2


@register_preset(
    id="clover_fill",
    label="Clover Fill",
    translations=(("zh", "三叶草填充"), ("ja", "クローバーフィル")),
)
def clover_fill(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _continuous_filling(frame, formation_index, drone_count, 0.6, 3)


@register_preset(
    id="continuous_filling_1",
    label="Continuous Filling 1",
    translations=(("zh", "连续填充1"), ("ja", "連続フィル1")),
)
def continuous_filling_1(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _continuous_filling(frame, formation_index, drone_count, 1.0, 3)


@register_preset(
    id="continuous_filling_1_5",
    label="Continuous Filling 1.5",
    translations=(("zh", "连续填充1.5"), ("ja", "連続フィル1.5")),
)
def continuous_filling_1_5(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _continuous_filling(frame, formation_index, drone_count, 1.5, 10)


@register_preset(
    id="continuous_filling_2",
    label="Continuous Filling 2",
    translations=(("zh", "连续填充2"), ("ja", "連続フィル2")),
)
def continuous_filling_2(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _continuous_filling(frame, formation_index, drone_count, 2.0, 5)


@register_preset(
    id="continuous_filling_3",
    label="Continuous Filling 3",
    translations=(("zh", "连续填充3"), ("ja", "連続フィル3")),
)
def continuous_filling_3(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _continuous_filling(frame, formation_index, drone_count, 3.0, 5)


@register_preset(
    id="continuous_filling_4",
    label="Continuous Filling 4",
    translations=(("zh", "连续填充4"), ("ja", "連続フィル4")),
)
def continuous_filling_4(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _continuous_filling(frame, formation_index, drone_count, 4.0, 5)


@register_preset(
    id="continuous_filling_5",
    label="Continuous Filling 5",
    translations=(("zh", "连续填充5"), ("ja", "連続フィル5")),
)
def continuous_filling_5(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _continuous_filling(frame, formation_index, drone_count, 5.0, 5)


@register_preset(
    id="continuous_filling_stripes",
    label="Continuous Stripes",
    translations=(("zh", "连续条纹填充"), ("ja", "連続ストライプ")),
)
def continuous_filling_stripes(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _continuous_filling(frame, formation_index, drone_count, 1.0, 5)
