from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import cos, float32, int32, sin, where
from numpy.typing import NDArray

from .base import register_preset
from .utils import get_centered_positions, get_formation_indices

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )

CHASE_SPEED = 0.12
CHASE_SPATIAL_K = 0.1


def _chasing_tails_core(
    positions: NDArray[float32], axis: int, frame: int, fi: NDArray[int32]
) -> NDArray[float32]:
    coord = positions[:, axis]
    travel_phase = frame * CHASE_SPEED - coord * CHASE_SPATIAL_K
    cos_result = (cos(travel_phase) + 1) / 2
    sin_result = (sin(travel_phase) + 1) / 2
    return where(fi % 2 == 0, sin_result, cos_result)


@register_preset(
    id="chasing_tails_x",
    label="Chasing Tails X",
    translations=(("zh", "追逐尾巴 X"), ("ja", "追跡 X")),
)
def chasing_tails_x(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    fi = get_formation_indices(context)
    out[:] = _chasing_tails_core(get_centered_positions(context), 0, frame, fi)


@register_preset(
    id="chasing_tails_y",
    label="Chasing Tails Y",
    translations=(("zh", "追逐尾巴 Y"), ("ja", "追跡 Y")),
)
def chasing_tails_y(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    fi = get_formation_indices(context)
    out[:] = _chasing_tails_core(get_centered_positions(context), 1, frame, fi)


@register_preset(
    id="chasing_tails_z",
    label="Chasing Tails Z",
    translations=(("zh", "追逐尾巴 Z"), ("ja", "追跡 Z")),
)
def chasing_tails_z(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    fi = get_formation_indices(context)
    out[:] = _chasing_tails_core(get_centered_positions(context), 2, frame, fi)
