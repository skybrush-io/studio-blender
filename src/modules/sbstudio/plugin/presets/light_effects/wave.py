from __future__ import annotations

from math import pi
from typing import TYPE_CHECKING

from numpy import abs, clip, float32, sin
from numpy.typing import NDArray

from .base import register_preset
from .utils import get_centered_normalized_xy_distances

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


def _sine_distorted_phase(
    positions: NDArray[float32],
    axis: int,
    frame: int,
    *,
    speed: float = 0.05,
    spatial_k: float = 0.1,
    amplitude: float = 0.5,
) -> NDArray[float32]:
    """Returns the phase of a wave travelling along the given axis, distorted by a sine
    of the coordinate along that axis, wrapped to the [0; 1) range.
    """
    return (frame * speed + sin(positions[:, axis] * spatial_k) * amplitude) % 1.0


def _spatial_wave(
    positions: NDArray[float32],
    frame: int,
    *,
    kx: float,
    ky: float,
    speed: float = 0.1,
) -> NDArray[float32]:
    """Returns a clipped pulse wave travelling in the XY plane, with its phase advancing
    linearly along the X and Y axes.
    """
    phase = (frame * speed + positions[:, 0] * kx + positions[:, 1] * ky) / 2 / pi
    v = (phase - phase.astype(int)).astype(float32)
    return clip(1.5 - abs(v - 0.5) * 4, 0, 1)


@register_preset(
    id="wave_sawtooth",
    label="Sawtooth Wave",
    translations=(("zh", "锯齿波"), ("ja", "ノコギリ波")),
)
def wave_sawtooth(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _sine_distorted_phase(context.positions.as_array, 0, frame).astype(float32)


@register_preset(
    id="wave_sawtooth_2",
    label="Sawtooth Wave 2",
    translations=(("zh", "锯齿波2"), ("ja", "ノコギリ波2")),
)
def wave_sawtooth_2(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _sine_distorted_phase(context.positions.as_array, 1, frame).astype(float32)


@register_preset(
    id="wave_sawtooth_3",
    label="Sawtooth Wave 3",
    translations=(("zh", "锯齿波3"), ("ja", "ノコギリ波3")),
)
def wave_sawtooth_3(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _sine_distorted_phase(context.positions.as_array, 2, frame).astype(float32)


@register_preset(
    id="wave_triangle",
    label="Triangle Wave",
    translations=(("zh", "三角波"), ("ja", "三角波")),
)
def wave_triangle(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    v = _sine_distorted_phase(
        context.positions.as_array, 0, frame, speed=0.04, spatial_k=0.05, amplitude=1.0
    )
    out[:] = (1 - abs(2 * v - 1)).astype(float32)


@register_preset(
    id="expanding_pulse",
    label="Expanding Pulse",
    translations=(("zh", "扩张脉冲"), ("ja", "拡張パルス")),
)
def expanding_pulse(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    relative_distances = get_centered_normalized_xy_distances(context)
    v = (frame * 0.04 - relative_distances) % 1.0
    out[:] = (1 - abs(2 * v - 1)).astype(float32)


@register_preset(
    id="sawtooth_pulse",
    label="Sawtooth Pulse",
    translations=(("zh", "锯齿脉冲"), ("ja", "ノコギリパルス")),
)
def sawtooth_pulse(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    relative_distances = get_centered_normalized_xy_distances(context)
    v = (frame * 0.04 - relative_distances) % 1.0
    out[:] = v.astype(float32)


@register_preset(
    id="spatial_wave",
    label="Spatial Wave",
    translations=(("zh", "空间波动"), ("ja", "空間波")),
)
def spatial_wave(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _spatial_wave(context.positions.as_array, frame, kx=0.2, ky=0.1)


@register_preset(
    id="spatial_wave_2",
    label="Spatial Wave 2",
    translations=(("zh", "空间波动2"), ("ja", "空間波2")),
)
def spatial_wave_2(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _spatial_wave(context.positions.as_array, frame, kx=0.1, ky=0.3)
