from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import clip, float32, pi, sin
from numpy.typing import NDArray

from .base import register_preset
from .utils import get_formation_indices

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


@register_preset(
    id="odd_even_pulse",
    label="Odd-Even Pulse",
    translations=(("zh", "奇偶脉冲"), ("ja", "奇数偶数パルス")),
)
def odd_even_pulse(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    fi = get_formation_indices(context)
    out[:] = (sin(frame * 0.1 + (fi % 2) * pi) + 1) / 2


@register_preset(
    id="odd_even_constant",
    label="Odd-Even Constant",
    translations=(("zh", "奇偶恒亮"), ("ja", "奇数偶数定常")),
)
def odd_even_constant(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    fi = get_formation_indices(context)
    out[:] = fi % 2


@register_preset(
    id="simple_filling",
    label="Simple Gradient Fill",
    translations=(("zh", "简单渐亮"), ("ja", "シンプルグラデーション")),
)
def simple_filling(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    N = len(out)
    if N == 0:
        return

    fi = get_formation_indices(context, dtype=float32)
    time_fraction = effect.get_time_fraction_for_frame(frame)

    if N > 1:
        out[:] = 2 * time_fraction - fi / (N - 1)
        clip(out, 0, 1)
    else:
        out[:] = time_fraction
