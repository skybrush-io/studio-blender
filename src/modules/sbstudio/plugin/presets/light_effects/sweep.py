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


def _v51_gradient_sweep_oneway_loop(coord: float, direction: int, frame: int) -> float:
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


def _v51_gradient_sweep_diagonal(
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


def _get_axis_coord(position, axis: str) -> float:
    if position is None:
        return 0.0
    coords = {"X": position[0], "Y": position[1], "Z": position[2]}
    return coords[axis.upper()]


# 3. Roundtrip Sweep (往返扫光) - 6 presets
@register_preset(
    id="roundtrip_sweep_ltr_xy",
    label="Roundtrip Sweep L→R XY",
    translations=(("zh", "往返扫光 左到右 XY"), ("ja", "往復スイープ 左→右 XY")),
)
def roundtrip_sweep_ltr_xy(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    coord = _get_axis_coord(position, "X")
    return _gradient_sweep_roundtrip(coord, +1, frame)


@register_preset(
    id="roundtrip_sweep_rtl_xy",
    label="Roundtrip Sweep R→L XY",
    translations=(("zh", "往返扫光 右到左 XY"), ("ja", "往復スイープ 右→左 XY")),
)
def roundtrip_sweep_rtl_xy(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    coord = _get_axis_coord(position, "X")
    return _gradient_sweep_roundtrip(coord, -1, frame)


@register_preset(
    id="roundtrip_sweep_ltr_xz",
    label="Roundtrip Sweep L→R XZ",
    translations=(("zh", "往返扫光 左到右 XZ"), ("ja", "往復スイープ 左→右 XZ")),
)
def roundtrip_sweep_ltr_xz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    coord = _get_axis_coord(position, "X")
    return _gradient_sweep_roundtrip(coord, +1, frame)


@register_preset(
    id="roundtrip_sweep_rtl_xz",
    label="Roundtrip Sweep R→L XZ",
    translations=(("zh", "往返扫光 右到左 XZ"), ("ja", "往復スイープ 右→左 XZ")),
)
def roundtrip_sweep_rtl_xz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    coord = _get_axis_coord(position, "X")
    return _gradient_sweep_roundtrip(coord, -1, frame)


@register_preset(
    id="roundtrip_sweep_ltr_yz",
    label="Roundtrip Sweep L→R YZ",
    translations=(("zh", "往返扫光 左到右 YZ"), ("ja", "往復スイープ 左→右 YZ")),
)
def roundtrip_sweep_ltr_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    coord = _get_axis_coord(position, "Y")
    return _gradient_sweep_roundtrip(coord, +1, frame)


@register_preset(
    id="roundtrip_sweep_rtl_yz",
    label="Roundtrip Sweep R→L YZ",
    translations=(("zh", "往返扫光 右到左 YZ"), ("ja", "往復スイープ 右→左 YZ")),
)
def roundtrip_sweep_rtl_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    coord = _get_axis_coord(position, "Y")
    return _gradient_sweep_roundtrip(coord, -1, frame)


# 4. Oneway Sweep (单向扫光) - 6 presets
@register_preset(
    id="oneway_sweep_ltr_xy",
    label="Oneway Sweep L→R XY",
    translations=(("zh", "单向扫光 左到右 XY"), ("ja", "片道スイープ 左→右 XY")),
)
def oneway_sweep_ltr_xy(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    coord = _get_axis_coord(position, "X")
    return _v51_gradient_sweep_oneway_loop(coord, +1, frame)


@register_preset(
    id="oneway_sweep_rtl_xy",
    label="Oneway Sweep R→L XY",
    translations=(("zh", "单向扫光 右到左 XY"), ("ja", "片道スイープ 右→左 XY")),
)
def oneway_sweep_rtl_xy(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    coord = _get_axis_coord(position, "X")
    return _v51_gradient_sweep_oneway_loop(coord, -1, frame)


@register_preset(
    id="oneway_sweep_ltr_xz",
    label="Oneway Sweep L→R XZ",
    translations=(("zh", "单向扫光 左到右 XZ"), ("ja", "片道スイープ 左→右 XZ")),
)
def oneway_sweep_ltr_xz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    coord = _get_axis_coord(position, "X")
    return _v51_gradient_sweep_oneway_loop(coord, +1, frame)


@register_preset(
    id="oneway_sweep_rtl_xz",
    label="Oneway Sweep R→L XZ",
    translations=(("zh", "单向扫光 右到左 XZ"), ("ja", "片道スイープ 右→左 XZ")),
)
def oneway_sweep_rtl_xz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    coord = _get_axis_coord(position, "X")
    return _v51_gradient_sweep_oneway_loop(coord, -1, frame)


@register_preset(
    id="oneway_sweep_ltr_yz",
    label="Oneway Sweep L→R YZ",
    translations=(("zh", "单向扫光 左到右 YZ"), ("ja", "片道スイープ 左→右 YZ")),
)
def oneway_sweep_ltr_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    coord = _get_axis_coord(position, "Y")
    return _v51_gradient_sweep_oneway_loop(coord, +1, frame)


@register_preset(
    id="oneway_sweep_rtl_yz",
    label="Oneway Sweep R→L YZ",
    translations=(("zh", "单向扫光 右到左 YZ"), ("ja", "片道スイープ 右→左 YZ")),
)
def oneway_sweep_rtl_yz(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    coord = _get_axis_coord(position, "Y")
    return _v51_gradient_sweep_oneway_loop(coord, -1, frame)


# 5. Diagonal Sweep (倾斜扫光) - 6 presets
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
    pos_a = _get_axis_coord(position, "X")
    pos_b = _get_axis_coord(position, "Y")
    return _v51_gradient_sweep_diagonal(pos_a, pos_b, +1, frame)


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
    pos_a = _get_axis_coord(position, "X")
    pos_b = _get_axis_coord(position, "Y")
    return _v51_gradient_sweep_diagonal(pos_a, pos_b, -1, frame)


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
    pos_a = _get_axis_coord(position, "X")
    pos_b = _get_axis_coord(position, "Z")
    return _v51_gradient_sweep_diagonal(pos_a, pos_b, +1, frame)


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
    pos_a = _get_axis_coord(position, "X")
    pos_b = _get_axis_coord(position, "Z")
    return _v51_gradient_sweep_diagonal(pos_a, pos_b, -1, frame)


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
    pos_a = _get_axis_coord(position, "Y")
    pos_b = _get_axis_coord(position, "Z")
    return _v51_gradient_sweep_diagonal(pos_a, pos_b, +1, frame)


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
    pos_a = _get_axis_coord(position, "Y")
    pos_b = _get_axis_coord(position, "Z")
    return _v51_gradient_sweep_diagonal(pos_a, pos_b, -1, frame)
