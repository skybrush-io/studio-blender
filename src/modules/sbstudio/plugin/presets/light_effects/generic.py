from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import float32
from numpy.typing import NDArray

from .base import register_preset
from .utils import (
    formation_index_phase,
    formation_index_sine_pulse,
    get_formation_indices,
    get_time,
)
from .waveforms import sine_wave, triangle_wave

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


@register_preset(
    id="lightfx_0",
    label="Light FX 0",
    translations=(("zh", "灯效0"), ("ja", "ライトFX 0")),
)
def lightfx_0(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = formation_index_sine_pulse(context, frame, divisor=25, speed=0.5, span=1.5)


@register_preset(
    id="lightfx_1",
    label="Light FX 1",
    translations=(("zh", "灯效1"), ("ja", "ライトFX 1")),
)
def lightfx_1(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = formation_index_sine_pulse(context, frame, divisor=5, speed=0.5, span=1.5)


@register_preset(
    id="lightfx_4",
    label="Light FX 4",
    translations=(("zh", "灯效4"), ("ja", "ライトFX 4")),
)
def lightfx_4(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    fi = get_formation_indices(context)
    is_odd = fi % 2
    out[:] = sine_wave(get_time(context, frame) * 0.76 + is_odd / 2)


@register_preset(
    id="lightfx_6",
    label="Light FX 6",
    translations=(("zh", "灯效6"), ("ja", "ライトFX 6")),
)
def lightfx_6(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = formation_index_phase(context, frame, wave_length=50, speed=0.48).astype(
        float32
    )


@register_preset(
    id="lightfx_7",
    label="Light FX 7",
    translations=(("zh", "灯效7"), ("ja", "ライトFX 7")),
)
def lightfx_7(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    v = formation_index_phase(context, frame, wave_length=400, speed=0.06)
    out[:] = triangle_wave(v)


@register_preset(
    id="lightfx_8",
    label="Light FX 8",
    translations=(("zh", "灯效8"), ("ja", "ライトFX 8")),
)
def lightfx_8(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = formation_index_sine_pulse(
        context, frame, divisor=1, speed=-0.0764, span=0.75
    )
