from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import float32, hypot, sin
from numpy.typing import NDArray

from .base import register_preset

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


@register_preset(
    id="radial_diffusion",
    label="Radial Diffusion",
    translations=(("zh", "径向扩散"), ("ja", "放射状拡散")),
)
def radial_diffusion(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    positions = context.positions.as_array
    cx, cy, _ = context.swarm_center.as_array
    r = hypot(positions[:, 0] - cx, positions[:, 1] - cy)
    r_max = r.max() if len(r) > 0 else 1.0
    if r_max == 0:
        r_max = 1.0
    tau = (r / r_max - frame * 0.01) % 1.0
    out[:] = ((sin(tau * 2 * 3.14159) + 1) / 2).astype(float32)


@register_preset(
    id="radial_diffusion_2",
    label="Radial Diffusion 2",
    translations=(("zh", "径向扩散2"), ("ja", "放射状拡散2")),
)
def radial_diffusion_2(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    positions = context.positions.as_array
    cx, cy, _ = context.swarm_center.as_array
    r = hypot(positions[:, 0] - cx, positions[:, 1] - cy)
    r_max = r.max() if len(r) > 0 else 1.0
    if r_max == 0:
        r_max = 1.0
    tau = (r / r_max + frame * 0.01) % 1.0
    out[:] = ((sin(tau * 2 * 3.14159) + 1) / 2).astype(float32)


@register_preset(
    id="radial_diffusion_3",
    label="Radial Diffusion 3",
    translations=(("zh", "径向扩散3"), ("ja", "放射状拡散3")),
)
def radial_diffusion_3(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    positions = context.positions.as_array
    cx, cy, _ = context.swarm_center.as_array
    r = hypot(positions[:, 0] - cx, positions[:, 1] - cy)
    r_max = r.max() if len(r) > 0 else 1.0
    if r_max == 0:
        r_max = 1.0
    tau = (r / r_max - frame * 0.005) % 1.0
    out[:] = ((sin(tau * 4 * 3.14159) + 1) / 2).astype(float32)


@register_preset(
    id="radial_convergence",
    label="Radial Convergence",
    translations=(("zh", "径向汇聚"), ("ja", "放射状収束")),
)
def radial_convergence(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    positions = context.positions.as_array
    cx, cy, _ = context.swarm_center.as_array
    r = hypot(positions[:, 0] - cx, positions[:, 1] - cy)
    r_max = r.max() if len(r) > 0 else 1.0
    if r_max == 0:
        r_max = 1.0
    tau = (1 - r / r_max - frame * 0.01) % 1.0
    out[:] = ((sin(tau * 2 * 3.14159) + 1) / 2).astype(float32)


@register_preset(
    id="radial_convergence_2",
    label="Radial Convergence 2",
    translations=(("zh", "径向汇聚2"), ("ja", "放射状収束2")),
)
def radial_convergence_2(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    positions = context.positions.as_array
    cx, cy, _ = context.swarm_center.as_array
    r = hypot(positions[:, 0] - cx, positions[:, 1] - cy)
    r_max = r.max() if len(r) > 0 else 1.0
    if r_max == 0:
        r_max = 1.0
    tau = (1 - r / r_max + frame * 0.01) % 1.0
    out[:] = ((sin(tau * 2 * 3.14159) + 1) / 2).astype(float32)


@register_preset(
    id="radial_convergence_3",
    label="Radial Convergence 3",
    translations=(("zh", "径向汇聚3"), ("ja", "放射状収束3")),
)
def radial_convergence_3(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    positions = context.positions.as_array
    cx, cy, _ = context.swarm_center.as_array
    r = hypot(positions[:, 0] - cx, positions[:, 1] - cy)
    r_max = r.max() if len(r) > 0 else 1.0
    if r_max == 0:
        r_max = 1.0
    tau = (1 - r / r_max - frame * 0.005) % 1.0
    out[:] = ((sin(tau * 4 * 3.14159) + 1) / 2).astype(float32)
