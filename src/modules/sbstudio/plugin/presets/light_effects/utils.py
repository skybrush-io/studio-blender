from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import array, empty, int32
from numpy.typing import NDArray

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import LightEffectEvaluationContext


def get_formation_indices(
    context: LightEffectEvaluationContext, *, default: int = 0, dtype=int32
) -> NDArray[int32]:
    """Returns the formation index for each drone as an int32 array.

    Drones with no formation mapping get ``default`` (0 by default).
    """
    if context.mapping is None:
        result = empty(context.num_drones, dtype=dtype)
        result.fill(default)
    else:
        result = array(
            [default if x is None else x for x in context.mapping], dtype=dtype
        )

    return result
