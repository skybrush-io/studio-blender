from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import array, empty, float32, hypot, int32, subtract, zeros
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


def get_centered_positions(context: LightEffectEvaluationContext) -> NDArray[float32]:
    """Returns drone positions centered around the swarm's barycenter.

    Returns an empty array of the same shape if there are no drones.
    """
    positions = context.positions.as_array
    if len(positions) == 0:
        return zeros((0, positions.shape[-1]), dtype=float32)
    center = context.swarm_center
    return subtract(positions, center, dtype=float32)


def get_centered_normalized_xy_distances(
    context: LightEffectEvaluationContext,
) -> NDArray[float32]:
    """Returns the distance of each drone from the swarm's barycenter in the XY plane,
    normalized to the [0; 1] range such that the farthest drone is at 1.0.

    Returns an empty array if there are no drones, and all zeros if all drones are
    located exactly at the barycenter.
    """
    positions = context.positions.as_array
    if len(positions) == 0:
        return zeros(0, dtype=float32)
    center = context.swarm_center
    radii = hypot(positions[:, 0] - center[0], positions[:, 1] - center[1])
    max_radius = radii.max()
    if max_radius > 0:
        radii /= max_radius
    return radii.astype(float32)
