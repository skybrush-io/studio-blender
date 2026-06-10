from __future__ import annotations

from math import sin
from typing import TYPE_CHECKING

from .base import register_preset

if TYPE_CHECKING:
    from sbstudio.model.types import Coordinate3D


@register_preset(
    id="ramp_down_wave",
    label="Ramp-Down Wave",
    translations=(("zh", "递减坡形波"), ("ja", "ランプダウン波")),
)
def ramp_down_wave(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    wave_length = 50
    return 1 - ((frame + (formation_index or 0)) % wave_length / wave_length)


def _ramp_up(frame, formation_index, wave_length) -> float:
    return (frame + (formation_index or 0)) % wave_length / wave_length


@register_preset(
    id="ramp_up_wave_10",
    label="Ramp-Up Wave 10",
    translations=(("zh", "递增坡形波10"), ("ja", "ランプアップ波10")),
)
def ramp_up_wave_10(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _ramp_up(frame, formation_index, 10)


@register_preset(
    id="ramp_up_wave_15",
    label="Ramp-Up Wave 15",
    translations=(("zh", "递增坡形波15"), ("ja", "ランプアップ波15")),
)
def ramp_up_wave_15(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _ramp_up(frame, formation_index, 15)


@register_preset(
    id="ramp_up_wave_25",
    label="Ramp-Up Wave 25",
    translations=(("zh", "递增坡形波25"), ("ja", "ランプアップ波25")),
)
def ramp_up_wave_25(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _ramp_up(frame, formation_index, 25)


@register_preset(
    id="ramp_up_wave_75",
    label="Ramp-Up Wave 75",
    translations=(("zh", "递增坡形波75"), ("ja", "ランプアップ波75")),
)
def ramp_up_wave_75(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _ramp_up(frame, formation_index, 75)


@register_preset(
    id="ramp_up_wave_100",
    label="Ramp-Up Wave 100",
    translations=(("zh", "递增坡形波100"), ("ja", "ランプアップ波100")),
)
def ramp_up_wave_100(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _ramp_up(frame, formation_index, 100)


@register_preset(
    id="ramp_up_wave_150",
    label="Ramp-Up Wave 150",
    translations=(("zh", "递增坡形波150"), ("ja", "ランプアップ波150")),
)
def ramp_up_wave_150(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    return _ramp_up(frame, formation_index, 150)


@register_preset(
    id="triangle_wave",
    label="Triangle Wave",
    translations=(("zh", "三角波"), ("ja", "三角波")),
)
def triangle_wave(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    wave_length = 50
    offset = (frame + (formation_index or 0)) % wave_length / wave_length
    return 1 - abs(2 * offset - 1)


@register_preset(
    id="expanding_pulse",
    label="Expanding Pulse",
    translations=(("zh", "扩散脉冲"), ("ja", "拡散パルス")),
)
def expanding_pulse(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    fi = formation_index or 0
    pulse_center = drone_count // 1 if drone_count else 0
    distance_from_center = abs(fi - pulse_center)
    pulse = (sin(frame * 0.1 - distance_from_center * 0.01) + 0.5) / 2
    # Clamp into [0, 1] (the original returned [-0.25, 0.75])
    return max(0.0, min(1.0, pulse))


@register_preset(
    id="wave_effect",
    label="Spatial Wave",
    description="Sinusoidal wave traveling along the world X axis",
    translations=(("zh", "空间波纹"), ("ja", "空間波")),
)
def wave_effect(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    speed = 0.1
    distance = position[0] if position is not None else 0.0
    return (sin(frame * speed - distance) + 1) / 2
