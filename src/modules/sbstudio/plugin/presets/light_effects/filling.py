from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import float32, maximum, pi
from numpy.typing import NDArray

from .base import register_preset
from .utils import get_formation_indices
from .waveforms import sine_wave

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


def _continuous_filling(
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    speed_factor: float,
    divisor: int,
) -> NDArray[float32]:
    """Returns a continuous sine filling pattern over the formation index, with
    ``divisor`` waves stretched across the whole swarm."""
    wave_length = maximum(context.num_drones / divisor, 1e-6)
    fi = get_formation_indices(context)
    offset = (fi % wave_length) / wave_length
    return sine_wave(frame * 0.1 * speed_factor + offset * 2 * pi)


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
    out[:] = _continuous_filling(context, frame, speed_factor=0.6, divisor=3)


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
    out[:] = _continuous_filling(context, frame, speed_factor=1.0, divisor=3)


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
    out[:] = _continuous_filling(context, frame, speed_factor=1.5, divisor=10)


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
    out[:] = _continuous_filling(context, frame, speed_factor=2.0, divisor=5)


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
    out[:] = _continuous_filling(context, frame, speed_factor=3.0, divisor=5)


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
    out[:] = _continuous_filling(context, frame, speed_factor=4.0, divisor=5)


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
    out[:] = _continuous_filling(context, frame, speed_factor=5.0, divisor=5)


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
    out[:] = _continuous_filling(context, frame, speed_factor=1.0, divisor=5)
