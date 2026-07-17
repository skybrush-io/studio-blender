from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import abs, clip, float32, sqrt, zeros
from numpy.typing import NDArray

from .base import register_preset

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


def _axis_sweep_on(
    positions: NDArray[float32], axis: int, frame: int, negate: bool = False
) -> NDArray[float32]:
    n = len(positions)
    if n == 0:
        return zeros(0, dtype=float32)
    x = positions[:, axis] / 100  # normalize roughly
    v = (frame * 0.04 + x) % 1.0 if not negate else (frame * 0.04 - x) % 1.0
    return (1 - abs(2 * v - 1)).astype(float32)


def _axis_sweep_off(
    positions: NDArray[float32], axis: int, frame: int
) -> NDArray[float32]:
    return 1 - _axis_sweep_on(positions, axis, frame, negate=False)


def _radial_sweep_on(
    positions: NDArray[float32], cx: float, cy: float, frame: int
) -> NDArray[float32]:
    n = len(positions)
    if n == 0:
        return zeros(0, dtype=float32)
    dx = positions[:, 0] - cx
    dy = positions[:, 1] - cy
    r = sqrt(dx * dx + dy * dy)
    r_max = r.max() if len(r) > 0 else 1.0
    if r_max == 0:
        r_max = 1.0
    v = (frame * 0.05 + r / r_max) % 1.0
    return (1 - abs(2 * v - 1)).astype(float32)


def _radial_sweep_off(
    positions: NDArray[float32], cx: float, cy: float, frame: int
) -> NDArray[float32]:
    return 1 - _radial_sweep_on(positions, cx, cy, frame)


@register_preset(
    id="sweep_positive_x",
    label="Sweep Positive X",
    translations=(("zh", "X正方向扫描"), ("ja", "スイープXプラス")),
)
def sweep_positive_x(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _axis_sweep_on(context.positions.as_array, 0, frame, negate=False)


@register_preset(
    id="sweep_positive_y",
    label="Sweep Positive Y",
    translations=(("zh", "Y正方向扫描"), ("ja", "スイープYプラス")),
)
def sweep_positive_y(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _axis_sweep_on(context.positions.as_array, 1, frame, negate=False)


@register_preset(
    id="sweep_positive_z",
    label="Sweep Positive Z",
    translations=(("zh", "Z正方向扫描"), ("ja", "スイープZプラス")),
)
def sweep_positive_z(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _axis_sweep_on(context.positions.as_array, 2, frame, negate=False)


@register_preset(
    id="sweep_negative_x",
    label="Sweep Negative X",
    translations=(("zh", "X负方向扫描"), ("ja", "スイープXマイナス")),
)
def sweep_negative_x(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _axis_sweep_on(context.positions.as_array, 0, frame, negate=True)


@register_preset(
    id="sweep_negative_y",
    label="Sweep Negative Y",
    translations=(("zh", "Y负方向扫描"), ("ja", "スイープYマイナス")),
)
def sweep_negative_y(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _axis_sweep_on(context.positions.as_array, 1, frame, negate=True)


@register_preset(
    id="sweep_negative_z",
    label="Sweep Negative Z",
    translations=(("zh", "Z负方向扫描"), ("ja", "スイープZマイナス")),
)
def sweep_negative_z(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _axis_sweep_on(context.positions.as_array, 2, frame, negate=True)


@register_preset(
    id="sweep_positive_x_off",
    label="Sweep Positive X Off",
    translations=(("zh", "X正方向扫描熄灭"), ("ja", "スイープXプラスオフ")),
)
def sweep_positive_x_off(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _axis_sweep_off(context.positions.as_array, 0, frame)


@register_preset(
    id="sweep_positive_y_off",
    label="Sweep Positive Y Off",
    translations=(("zh", "Y正方向扫描熄灭"), ("ja", "スイープYプラスオフ")),
)
def sweep_positive_y_off(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _axis_sweep_off(context.positions.as_array, 1, frame)


@register_preset(
    id="sweep_positive_z_off",
    label="Sweep Positive Z Off",
    translations=(("zh", "Z正方向扫描熄灭"), ("ja", "スイープZプラスオフ")),
)
def sweep_positive_z_off(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _axis_sweep_off(context.positions.as_array, 2, frame)


@register_preset(
    id="sweep_negative_x_off",
    label="Sweep Negative X Off",
    translations=(("zh", "X负方向扫描熄灭"), ("ja", "スイープXマイナスオフ")),
)
def sweep_negative_x_off(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _axis_sweep_on(context.positions.as_array, 0, frame, negate=True)
    out[:] = 1 - out


@register_preset(
    id="sweep_negative_y_off",
    label="Sweep Negative Y Off",
    translations=(("zh", "Y负方向扫描熄灭"), ("ja", "スイープYマイナスオフ")),
)
def sweep_negative_y_off(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _axis_sweep_on(context.positions.as_array, 1, frame, negate=True)
    out[:] = 1 - out


@register_preset(
    id="sweep_negative_z_off",
    label="Sweep Negative Z Off",
    translations=(("zh", "Z负方向扫描熄灭"), ("ja", "スイープZマイナスオフ")),
)
def sweep_negative_z_off(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    out[:] = _axis_sweep_on(context.positions.as_array, 2, frame, negate=True)
    out[:] = 1 - out


@register_preset(
    id="radial_sweep_on",
    label="Radial Sweep On",
    translations=(("zh", "径向向外扫描"), ("ja", "放射状スイープオン")),
)
def radial_sweep_on(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    cx, cy, _ = context.swarm_center.as_array
    out[:] = _radial_sweep_on(context.positions.as_array, cx, cy, frame)


@register_preset(
    id="radial_sweep_off",
    label="Radial Sweep Off",
    translations=(("zh", "径向向内扫描"), ("ja", "放射状スイープオフ")),
)
def radial_sweep_off(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    cx, cy, _ = context.swarm_center.as_array
    out[:] = _radial_sweep_off(context.positions.as_array, cx, cy, frame)


@register_preset(
    id="radial_sweep_on_2",
    label="Radial Sweep On 2",
    translations=(("zh", "径向向外扫描2"), ("ja", "放射状スイープオン2")),
)
def radial_sweep_on_2(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    cx, cy, _ = context.swarm_center.as_array
    v = _radial_sweep_on(context.positions.as_array, cx, cy, frame)
    out[:] = clip(2 * (v - 0.25), 0, 1)


@register_preset(
    id="radial_sweep_off_2",
    label="Radial Sweep Off 2",
    translations=(("zh", "径向向内扫描2"), ("ja", "放射状スイープオフ2")),
)
def radial_sweep_off_2(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    cx, cy, _ = context.swarm_center.as_array
    v = _radial_sweep_off(context.positions.as_array, cx, cy, frame)
    out[:] = clip(2 * (v - 0.25), 0, 1)
