from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import float32, int32, select
from numpy.typing import NDArray

from .base import register_preset
from .utils import get_formation_indices

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )

# TODO(ntamas): the range tables are hard-coded for formations with exactly
# 100 drones; this should eventually become a configurable parameter on the
# light effect

_RANGES_3 = (
    (0, 17, 0.1),
    (18, 35, 0.2),
    (36, 53, 0.4),
    (54, 71, 0.3),
    (72, 99, 0.5),
)

_RANGES_5 = (
    (0, 19, 0.2),
    (20, 39, 0.1),
    (36, 53, 0.4),
    (54, 71, 0.3),
    (72, 99, 0.5),
)


def _ranges_lookup(
    ranges: tuple[tuple[int, int, float], ...], fi: NDArray[int32]
) -> NDArray[float32]:
    conditions = [(fi >= start) & (fi <= end) for start, end, _ in ranges]
    values = [brightness for _, _, brightness in ranges]
    return select(conditions, values, default=0.0).astype(float32)


@register_preset(
    id="group_ranges_3",
    label="3 Group Ranges",
    description="Hard-coded 3-band brightness mapping by formation index",
    translations=(("zh", "三段亮度分区"), ("ja", "3グループ範囲")),
)
def group_ranges_3(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    fi = get_formation_indices(context)
    out[:] = _ranges_lookup(_RANGES_3, fi)


@register_preset(
    id="group_ranges_5",
    label="5 Group Ranges",
    description="Hard-coded 5-band brightness mapping by formation index",
    translations=(("zh", "五段亮度分区"), ("ja", "5グループ範囲")),
)
def group_ranges_5(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    fi = get_formation_indices(context)
    out[:] = _ranges_lookup(_RANGES_5, fi)
