from __future__ import annotations

from math import pi, sin
from typing import TYPE_CHECKING

from .base import register_preset

if TYPE_CHECKING:
    from sbstudio.model.types import Coordinate3D


@register_preset(
    id="odd_even_pulse",
    label="Odd-Even Pulse",
    translations=(("zh", "奇偶脉冲"), ("ja", "奇数偶数パルス")),
)
def odd_even_pulse(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    is_odd = (formation_index or 0) % 2
    return (sin(frame * 0.1 + is_odd * pi) + 1) / 2


@register_preset(
    id="odd_even_constant",
    label="Odd-Even Constant",
    translations=(("zh", "奇偶恒亮"), ("ja", "奇数偶数定常")),
)
def odd_even_constant(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    is_odd = (formation_index or 0) % 2
    return 1.0 if is_odd else 0.5


@register_preset(
    id="simple_filling",
    label="Simple Gradient Fill",
    translations=(("zh", "简单渐亮"), ("ja", "シンプルグラデーション")),
)
def simple_filling(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    if not drone_count:
        return 0.0
    factor = (formation_index or 0) / drone_count
    return factor * time_fraction
