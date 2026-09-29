from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import float32, zeros
from numpy.typing import NDArray

from .base import register_preset
from .utils import get_formation_indices

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


def _group_ranges(
    context: LightEffectEvaluationContext, num_groups: int
) -> NDArray[float32]:
    """Splits the formation index into ``num_groups`` equally sized ranges and maps them
    to evenly spaced brightness levels from 0 to 1.

    Returns an empty array if there are no drones.

    Function implicitly assumes that the formation index is smaller
    than the number of drones.
    """
    num_drones = context.num_drones
    if num_drones == 0:
        return zeros(0, dtype=float32)
    fi = get_formation_indices(context)
    group = (fi * num_groups) // num_drones
    return (group / (num_groups - 1)).astype(float32)


@register_preset(
    id="group_ranges_3",
    label="3 Group Ranges",
    description="3-band brightness mapping by formation index",
    translations=(("zh", "三段亮度分区"), ("ja", "3グループ範囲")),
)
def group_ranges_3(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _group_ranges(context, 3)


@register_preset(
    id="group_ranges_5",
    label="5 Group Ranges",
    description="5-band brightness mapping by formation index",
    translations=(("zh", "五段亮度分区"), ("ja", "5グループ範囲")),
)
def group_ranges_5(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _group_ranges(context, 5)
