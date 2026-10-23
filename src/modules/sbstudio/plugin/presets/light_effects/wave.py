from __future__ import annotations

from math import tau
from typing import TYPE_CHECKING

from numpy import float32, sin
from numpy.typing import NDArray

from .base import register_preset
from .utils import (
    get_centered_normalized_xy_distances,
    get_centered_positions,
    get_time,
)
from .waveforms import steepen, triangle_wave

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


def _sine_distorted_phase(
    context: LightEffectEvaluationContext,
    axis: int,
    frame: int,
    *,
    speed: float = 1.2,
    spatial_k: float = 0.016,
    amplitude: float = 0.5,
) -> NDArray[float32]:
    """Returns the phase of a wave travelling along the given axis, distorted by a sine of
    the coordinate along that axis.

    Args:
        context: evaluation context for the swarm
        axis: index of the axis along which the wave travels
        frame: current frame number
        speed: temporal speed of the wave, in cycles per second
        spatial_k: spatial frequency along the axis, in wave cycles per unit distance
        amplitude: strength of the spatial distortion, in phase turns

    Returns:
        per-drone phase, wrapped to [0, 1).
    """
    positions = get_centered_positions(context)
    return (
        get_time(context, frame) * speed
        + sin(positions[:, axis] * spatial_k * tau) * amplitude
    ) % 1.0


def _spatial_wave(
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    kx: float,
    ky: float,
    speed: float = 0.38,
) -> NDArray[float32]:
    """Returns a clipped pulse wave travelling in the XY plane, with its phase advancing
    linearly along the X and Y axes.

    Args:
        context: evaluation context for the swarm
        frame: current frame number
        kx: spatial frequency along the X axis, in wave cycles per unit distance
        ky: spatial frequency along the Y axis, in wave cycles per unit distance
        speed: temporal speed of the wave, in cycles per second

    Returns:
        per-drone brightness of the clipped pulse, in [0, 1].
    """
    positions = get_centered_positions(context)
    phase = (
        get_time(context, frame) * speed + positions[:, 0] * kx + positions[:, 1] * ky
    )
    return steepen(triangle_wave(phase))


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
    out[:] = _sine_distorted_phase(context, 0, frame)


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
    out[:] = _sine_distorted_phase(context, 1, frame)


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
    out[:] = _sine_distorted_phase(context, 2, frame)


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
        context, 0, frame, speed=0.96, spatial_k=0.008, amplitude=1.0
    )
    out[:] = triangle_wave(v)


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
    out[:] = triangle_wave(get_time(context, frame) * 0.96 - relative_distances)


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
    v = (get_time(context, frame) * 0.96 - relative_distances) % 1.0
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
    out[:] = _spatial_wave(context, frame, kx=0.032, ky=0.016)


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
    out[:] = _spatial_wave(context, frame, kx=0.016, ky=0.048)
