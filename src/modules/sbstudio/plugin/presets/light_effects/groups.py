from __future__ import annotations

from typing import TYPE_CHECKING

from .base import register_preset

if TYPE_CHECKING:
    from sbstudio.model.types import Coordinate3D


def _ranges_lookup(ranges, formation_index) -> float:
    fi = formation_index or 0
    for start, end, brightness in ranges:
        if start <= fi <= end:
            return brightness
    return 0.0


@register_preset(
    id="group_ranges_3",
    label="3 Group Ranges",
    description="Hard-coded 3-band brightness mapping by formation index",
    translations=(("zh", "三段亮度分区"), ("ja", "3グループ範囲")),
)
def group_ranges_3(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    ranges = [
        (0, 17, 0.1),
        (18, 35, 0.2),
        (36, 53, 0.4),
        (54, 71, 0.3),
        (72, 99, 0.5),
    ]
    return _ranges_lookup(ranges, formation_index)


@register_preset(
    id="group_ranges_5",
    label="5 Group Ranges",
    description="Hard-coded 5-band brightness mapping by formation index",
    translations=(("zh", "五段亮度分区"), ("ja", "5グループ範囲")),
)
def group_ranges_5(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    ranges = [
        (0, 19, 0.2),
        (20, 39, 0.1),
        (36, 53, 0.4),
        (54, 71, 0.3),
        (72, 99, 0.5),
    ]
    return _ranges_lookup(ranges, formation_index)
