from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import abs, float32, maximum, pi, sin
from numpy.typing import NDArray

from .base import register_preset
from .utils import get_formation_indices

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
    N = len(out)
    if N == 0:
        return
    fi = get_formation_indices(context)
    wave_length = maximum(N / 25, 1e-6)
    offset = (fi % wave_length) / wave_length
    out[:] = (sin(frame * 0.13 + offset * 3 * pi) + 1) / 2


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
    N = len(out)
    if N == 0:
        return
    fi = get_formation_indices(context)
    wave_length = maximum(N / 5, 1e-6)
    offset = (fi % wave_length) / wave_length
    out[:] = (sin(frame * 0.13 + offset * 3 * pi) + 1) / 2


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
    out[:] = (sin(frame * 0.2 + is_odd * pi) + 1) / 4


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
    fi = get_formation_indices(context)
    wave_length = 50
    out[:] = ((frame + fi) % wave_length / wave_length).astype(float32)


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
    fi = get_formation_indices(context)
    wave_length = 400
    offset = (frame + fi) % wave_length / wave_length
    out[:] = (1 - abs(2 * offset - 1)).astype(float32)


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
    N = len(out)
    if N == 0:
        return
    fi = get_formation_indices(context)
    speed_factor = -0.2
    wave_length = maximum(N / 1, 1e-6)
    offset = (fi % wave_length) / wave_length
    out[:] = (sin(frame * 0.1 * speed_factor + offset * 1.5 * pi) + 1) / 2
