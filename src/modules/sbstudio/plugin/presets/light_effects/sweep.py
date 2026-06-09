from __future__ import annotations

from math import sqrt
from typing import TYPE_CHECKING

from .base import register_preset

if TYPE_CHECKING:
    from sbstudio.model.types import Coordinate3D


SWEEP_RANGE_MIN = -30.0
SWEEP_RANGE_MAX = 30.0
SWEEP_ONEWAY_DURATION = 120
SWEEP_ONEWAY_PAUSE = 48
SWEEP_ROUNDTRIP_PAUSE = 24
SWEEP_GRADIENT_WIDTH = 8.0


def _gradient_sweep_roundtrip(coord: float, direction: int, frame: int) -> float:
    oneway_frames = SWEEP_ONEWAY_DURATION
    pause_frames = SWEEP_ROUNDTRIP_PAUSE
    full_cycle = 2 * (oneway_frames + pause_frames)
    t = frame % full_cycle
    if t < oneway_frames:
        phase = t / max(oneway_frames, 1)
    elif t < oneway_frames + pause_frames:
        phase = 1.0
    elif t < 2 * oneway_frames + pause_frames:
        phase = 1.0 - (t - oneway_frames - pause_frames) / max(oneway_frames, 1)
    else:
        phase = 0.0
    sweep_pos = SWEEP_RANGE_MIN + phase * (SWEEP_RANGE_MAX - SWEEP_RANGE_MIN)
    if direction < 0:
        sweep_pos = SWEEP_RANGE_MAX - (sweep_pos - SWEEP_RANGE_MIN)
    dist = abs(coord - sweep_pos)
    half_width = SWEEP_GRADIENT_WIDTH / 2.0
    if dist >= half_width:
        return 0.0
    brightness = 1.0 - (dist / half_width)
    return max(0.0, min(1.0, brightness))


def _gradient_sweep_oneway_loop(coord: float, direction: int, frame: int) -> float:
    oneway_frames = SWEEP_ONEWAY_DURATION
    pause_frames = SWEEP_ONEWAY_PAUSE
    full_cycle = oneway_frames + pause_frames
    t = frame % full_cycle
    if t < oneway_frames:
        phase = t / max(oneway_frames, 1)
    else:
        return 0.0
    if direction > 0:
        sweep_pos = SWEEP_RANGE_MIN + phase * (SWEEP_RANGE_MAX - SWEEP_RANGE_MIN)
    else:
        sweep_pos = SWEEP_RANGE_MAX - phase * (SWEEP_RANGE_MAX - SWEEP_RANGE_MIN)
    dist = abs(coord - sweep_pos)
    half_width = SWEEP_GRADIENT_WIDTH / 2.0
    if dist >= half_width:
        return 0.0
    brightness = 1.0 - (dist / half_width)
    return max(0.0, min(1.0, brightness))


def _gradient_sweep_diagonal(
    pos_a: float, pos_b: float, direction: int, frame: int
) -> float:
    proj = (pos_a + pos_b) / sqrt(2)
    oneway_frames = SWEEP_ONEWAY_DURATION
    pause_frames = SWEEP_ONEWAY_PAUSE
    full_cycle = oneway_frames + pause_frames
    t = frame % full_cycle
    if t < oneway_frames:
        phase = t / max(oneway_frames, 1)
    else:
        return 0.0
    if direction > 0:
        sweep_pos = SWEEP_RANGE_MIN + phase * (SWEEP_RANGE_MAX - SWEEP_RANGE_MIN)
    else:
        sweep_pos = SWEEP_RANGE_MAX - phase * (SWEEP_RANGE_MAX - SWEEP_RANGE_MIN)
    dist = abs(proj - sweep_pos)
    half_width = SWEEP_GRADIENT_WIDTH / 2.0
    if dist >= half_width:
        return 0.0
    brightness = 1.0 - (dist / half_width)
    return max(0.0, min(1.0, brightness))


@register_preset(
    id="roundtrip_sweep_ltr_x",
    label="Roundtrip Sweep L→R X",
    translations=(("zh", "往返扫光 左到右 X"), ("ja", "往復スイープ 左→右 X")),
)
def roundtrip_sweep_ltr_x(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_roundtrip(position[0], +1, frame)


@register_preset(
    id="roundtrip_sweep_rtl_x",
    label="Roundtrip Sweep R→L X",
    translations=(("zh", "往返扫光 右到左 X"), ("ja", "往復スイープ 右→左 X")),
)
def roundtrip_sweep_rtl_x(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_roundtrip(position[0], -1, frame)


@register_preset(
    id="roundtrip_sweep_ltr_y",
    label="Roundtrip Sweep L→R Y",
    translations=(("zh", "往返扫光 左到右 Y"), ("ja", "往復スイープ 左→右 Y")),
)
def roundtrip_sweep_ltr_y(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_roundtrip(position[1], +1, frame)


@register_preset(
    id="roundtrip_sweep_rtl_y",
    label="Roundtrip Sweep R→L Y",
    translations=(("zh", "往返扫光 右到左 Y"), ("ja", "往復スイープ 右→左 Y")),
)
def roundtrip_sweep_rtl_y(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_roundtrip(position[1], -1, frame)


@register_preset(
    id="roundtrip_sweep_ltr_z",
    label="Roundtrip Sweep L→R Z",
    translations=(("zh", "往返扫光 左到右 Z"), ("ja", "往復スイープ 左→右 Z")),
)
def roundtrip_sweep_ltr_z(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_roundtrip(position[2], +1, frame)


@register_preset(
    id="roundtrip_sweep_rtl_z",
    label="Roundtrip Sweep R→L Z",
    translations=(("zh", "往返扫光 右到左 Z"), ("ja", "往復スイープ 右→左 Z")),
)
def roundtrip_sweep_rtl_z(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_roundtrip(position[2], -1, frame)


@register_preset(
    id="oneway_sweep_ltr_x",
    label="Oneway Sweep L→R X",
    translations=(("zh", "单向扫光 左到右 X"), ("ja", "片道スイープ 左→右 X")),
)
def oneway_sweep_ltr_x(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_oneway_loop(position[0], +1, frame)


@register_preset(
    id="oneway_sweep_rtl_x",
    label="Oneway Sweep R→L X",
    translations=(("zh", "单向扫光 右到左 X"), ("ja", "片道スイープ 右→左 X")),
)
def oneway_sweep_rtl_x(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_oneway_loop(position[0], -1, frame)


@register_preset(
    id="oneway_sweep_ltr_y",
    label="Oneway Sweep L→R Y",
    translations=(("zh", "单向扫光 左到右 Y"), ("ja", "片道スイープ 左→右 Y")),
)
def oneway_sweep_ltr_y(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_oneway_loop(position[1], +1, frame)


@register_preset(
    id="oneway_sweep_rtl_y",
    label="Oneway Sweep R→L Y",
    translations=(("zh", "单向扫光 右到左 Y"), ("ja", "片道スイープ 右→左 Y")),
)
def oneway_sweep_rtl_y(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_oneway_loop(position[1], -1, frame)


@register_preset(
    id="oneway_sweep_ltr_z",
    label="Oneway Sweep L→R Z",
    translations=(("zh", "单向扫光 左到右 Z"), ("ja", "片道スイープ 左→右 Z")),
)
def oneway_sweep_ltr_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_oneway_loop(position[2], +1, frame)


@register_preset(
    id="oneway_sweep_rtl_z",
    label="Oneway Sweep R→L Z",
    translations=(("zh", "单向扫光 右到左 Z"), ("ja", "片道スイープ 右→左 Z")),
)
def oneway_sweep_rtl_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_oneway_loop(position[2], -1, frame)


@register_preset(
    id="diagonal_sweep_lb_rt_xy",
    label="Diagonal Sweep LB→RT XY",
    translations=(
        ("zh", "倾斜扫光 左下到右上 XY"),
        ("ja", "斜めスイープ 左下→右上 XY"),
    ),
)
def diagonal_sweep_lb_rt_xy(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_diagonal(position[0], position[1], +1, frame)


@register_preset(
    id="diagonal_sweep_rt_lb_xy",
    label="Diagonal Sweep RT→LB XY",
    translations=(
        ("zh", "倾斜扫光 右上到左下 XY"),
        ("ja", "斜めスイープ 右上→左下 XY"),
    ),
)
def diagonal_sweep_rt_lb_xy(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_diagonal(position[0], position[1], -1, frame)


@register_preset(
    id="diagonal_sweep_lb_rt_xz",
    label="Diagonal Sweep LB→RT XZ",
    translations=(
        ("zh", "倾斜扫光 左下到右上 XZ"),
        ("ja", "斜めスイープ 左下→右上 XZ"),
    ),
)
def diagonal_sweep_lb_rt_xz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_diagonal(position[0], position[2], +1, frame)


@register_preset(
    id="diagonal_sweep_rt_lb_xz",
    label="Diagonal Sweep RT→LB XZ",
    translations=(
        ("zh", "倾斜扫光 右上到左下 XZ"),
        ("ja", "斜めスイープ 右上→左下 XZ"),
    ),
)
def diagonal_sweep_rt_lb_xz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_diagonal(position[0], position[2], -1, frame)


@register_preset(
    id="diagonal_sweep_lb_rt_yz",
    label="Diagonal Sweep LB→RT YZ",
    translations=(
        ("zh", "倾斜扫光 左下到右上 YZ"),
        ("ja", "斜めスイープ 左下→右上 YZ"),
    ),
)
def diagonal_sweep_lb_rt_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_diagonal(position[1], position[2], +1, frame)


@register_preset(
    id="diagonal_sweep_rt_lb_yz",
    label="Diagonal Sweep RT→LB YZ",
    translations=(
        ("zh", "倾斜扫光 右上到左下 YZ"),
        ("ja", "斜めスイープ 右上→左下 YZ"),
    ),
)
def diagonal_sweep_rt_lb_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _gradient_sweep_diagonal(position[1], position[2], -1, frame)
