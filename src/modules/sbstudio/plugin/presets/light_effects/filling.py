from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import float32
from numpy.typing import NDArray

from .base import register_preset
from .utils import formation_index_sine_pulse

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


@register_preset(
    id="clover_fill",
    label="Clover Fill",
    translations=(("zh", "三叶草填充"), ("ja", "クローバーフィル")),
)
def clover_fill(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = formation_index_sine_pulse(context, frame, divisor=3, speed=0.23)


@register_preset(
    id="continuous_filling_1",
    label="Continuous Filling 1",
    translations=(("zh", "连续填充1"), ("ja", "連続フィル1")),
)
def continuous_filling_1(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = formation_index_sine_pulse(context, frame, divisor=3, speed=0.38)


@register_preset(
    id="continuous_filling_1_5",
    label="Continuous Filling 1.5",
    translations=(("zh", "连续填充1.5"), ("ja", "連続フィル1.5")),
)
def continuous_filling_1_5(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = formation_index_sine_pulse(context, frame, divisor=10, speed=0.57)


@register_preset(
    id="continuous_filling_2",
    label="Continuous Filling 2",
    translations=(("zh", "连续填充2"), ("ja", "連続フィル2")),
)
def continuous_filling_2(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = formation_index_sine_pulse(context, frame, divisor=5, speed=0.76)


@register_preset(
    id="continuous_filling_3",
    label="Continuous Filling 3",
    translations=(("zh", "连续填充3"), ("ja", "連続フィル3")),
)
def continuous_filling_3(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = formation_index_sine_pulse(context, frame, divisor=5, speed=1.15)


@register_preset(
    id="continuous_filling_4",
    label="Continuous Filling 4",
    translations=(("zh", "连续填充4"), ("ja", "連続フィル4")),
)
def continuous_filling_4(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = formation_index_sine_pulse(context, frame, divisor=5, speed=1.53)


@register_preset(
    id="continuous_filling_5",
    label="Continuous Filling 5",
    translations=(("zh", "连续填充5"), ("ja", "連続フィル5")),
)
def continuous_filling_5(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = formation_index_sine_pulse(context, frame, divisor=5, speed=1.91)


@register_preset(
    id="continuous_filling_stripes",
    label="Continuous Stripes",
    translations=(("zh", "连续条纹填充"), ("ja", "連続ストライプ")),
)
def continuous_filling_stripes(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = formation_index_sine_pulse(context, frame, divisor=5, speed=0.38)
