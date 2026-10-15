from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import array, empty, float32, hypot, int32, maximum, pi, subtract, zeros
from numpy.typing import NDArray

from .waveforms import sine_wave

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import LightEffectEvaluationContext


def get_formation_indices(
    context: LightEffectEvaluationContext, *, default: int = 0, dtype=int32
) -> NDArray[int32]:
    """Returns the formation index for each drone.

    ``default`` is used for drones with no formation mapping, and ``dtype`` is the integer
    type of the result.
    """
    if context.mapping is None:
        result = empty(context.num_drones, dtype=dtype)
        result.fill(default)
    else:
        result = array(
            [default if x is None else x for x in context.mapping], dtype=dtype
        )

    return result


def formation_index_sine_pulse(
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    divisor: float,
    speed: float,
    span: float = 2 * pi,
) -> NDArray[float32]:
    """Returns a sine pulse over the formation index.

    The formation index is wrapped into ``divisor`` waves across the whole swarm,
    so the pattern stretches with the number of drones.

    Args:
        context: evaluation context for the swarm
        frame: current frame number
        divisor: number of waves the formation index is wrapped into
        speed: phase advance per frame
        span: phase width of a single wave, in radians

    Returns:
        per-drone brightness of the sine pulse, in [0, 1].
    """
    wave_length = maximum(context.num_drones / divisor, 1e-6)
    fi = get_formation_indices(context)
    offset = (fi % wave_length) / wave_length
    return sine_wave(frame * speed + offset * span)


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
