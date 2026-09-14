from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import float32
from numpy.typing import NDArray

from .base import register_preset
from .utils import get_formation_indices

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


def _group_ranges(num_groups: int, out: NDArray[float32], context) -> None:
    N = len(out)
    if N == 0:
        return
    fi = get_formation_indices(context)
    group = (fi * num_groups) // N
    out[:] = group / (num_groups - 1)


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
    _group_ranges(3, out, context)


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
    _group_ranges(5, out, context)
