from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import abs, clip, float32, sin
from numpy.typing import NDArray

from .base import register_preset

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


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
    n = len(out)
    if n == 0:
        return
    positions = context.positions.as_array
    v = (frame * 0.05 + sin(positions[:, 0] * 0.1) * 0.5) % 1.0
    out[:] = v.astype(float32)


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
    n = len(out)
    if n == 0:
        return
    positions = context.positions.as_array
    v = (frame * 0.05 + sin(positions[:, 1] * 0.1) * 0.5) % 1.0
    out[:] = v.astype(float32)


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
    n = len(out)
    if n == 0:
        return
    positions = context.positions.as_array
    v = (frame * 0.05 + sin(positions[:, 2] * 0.1) * 0.5) % 1.0
    out[:] = v.astype(float32)


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
    n = len(out)
    if n == 0:
        return
    positions = context.positions.as_array
    v = (frame * 0.04 + sin(positions[:, 0] * 0.05)) % 1.0
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
    n = len(out)
    if n == 0:
        return
    positions = context.positions.as_array
    dx = positions[:, 0] - context.swarm_center.as_array[0]
    dy = positions[:, 1] - context.swarm_center.as_array[1]
    r = (dx * dx + dy * dy) ** 0.5
    r_max = r.max() if len(r) > 0 else 1.0
    if r_max == 0:
        r_max = 1.0
    v = (frame * 0.04 - r / r_max) % 1.0
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
    n = len(out)
    if n == 0:
        return
    positions = context.positions.as_array
    dx = positions[:, 0] - context.swarm_center.as_array[0]
    dy = positions[:, 1] - context.swarm_center.as_array[1]
    r = (dx * dx + dy * dy) ** 0.5
    r_max = r.max() if len(r) > 0 else 1.0
    if r_max == 0:
        r_max = 1.0
    v = (frame * 0.04 - r / r_max) % 1.0
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
    n = len(out)
    if n == 0:
        return
    positions = context.positions.as_array
    phase = (frame * 0.1 + positions[:, 0] * 0.2 + positions[:, 1] * 0.1) / 6.28
    v = (phase - phase.astype(int)).astype(float32)
    out[:] = clip(1.5 - abs(v - 0.5) * 4, 0, 1)


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
    n = len(out)
    if n == 0:
        return
    positions = context.positions.as_array
    phase = (frame * 0.1 + positions[:, 0] * 0.1 + positions[:, 1] * 0.3) / 6.28
    v = (phase - phase.astype(int)).astype(float32)
    out[:] = clip(1.5 - abs(v - 0.5) * 4, 0, 1)
