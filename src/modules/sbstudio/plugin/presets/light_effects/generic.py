from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import float32, float64, maximum, pi
from numpy.typing import NDArray

from .base import register_preset
from .utils import get_formation_indices
from .waveforms import sine_wave, triangle_wave

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


def _formation_index_sine_pulse(
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    divisor: float,
    speed: float,
    span: float,
) -> NDArray[float32]:
    """Returns a sine pulse over the formation index.

    The formation index is wrapped into ``divisor`` waves across the whole swarm, so the
    pattern stretches with the number of drones. ``span`` is the phase width of a single
    wave in radians.
    """
    wave_length = maximum(context.num_drones / divisor, 1e-6)
    fi = get_formation_indices(context)
    offset = (fi % wave_length) / wave_length
    return sine_wave(frame * speed + offset * span)


def _formation_index_phase(
    context: LightEffectEvaluationContext, frame: int, *, wave_length: int
) -> NDArray[float64]:
    """Returns the formation index offset by the current frame, wrapped into
    ``wave_length`` steps and normalized to the [0; 1) range."""
    fi = get_formation_indices(context)
    return (frame + fi) % wave_length / wave_length


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
    out[:] = _formation_index_sine_pulse(
        context, frame, divisor=25, speed=0.13, span=3 * pi
    )


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
    out[:] = _formation_index_sine_pulse(
        context, frame, divisor=5, speed=0.13, span=3 * pi
    )


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
    out[:] = sine_wave(frame * 0.2 + is_odd * pi) / 2


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
    out[:] = _formation_index_phase(context, frame, wave_length=50).astype(float32)


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
    v = _formation_index_phase(context, frame, wave_length=400)
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
    out[:] = _formation_index_sine_pulse(
        context, frame, divisor=1, speed=-0.02, span=1.5 * pi
    )
