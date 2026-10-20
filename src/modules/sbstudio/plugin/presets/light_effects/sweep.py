from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import float32
from numpy.typing import NDArray

from .base import register_preset
from .utils import get_centered_normalized_xy_distances, get_centered_positions
from .waveforms import steepen, triangle_wave

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


def _axis_sweep(
    context: LightEffectEvaluationContext,
    axis: int,
    frame: int,
    *,
    negate: bool = False,
    invert: bool = False,
) -> NDArray[float32]:
    """Returns a triangle wave travelling along the given axis, relative to the swarm
    barycenter.

    Args:
        context: evaluation context for the swarm
        axis: index of the axis along which the wave travels
        frame: current frame number
        negate: reverse the direction of travel
        invert: make the sweep dark instead of bright where it passes

    Returns:
        per-drone brightness of the sweep, in [0, 1].
    """
    x = get_centered_positions(context)[:, axis] / 100  # normalize roughly
    v = triangle_wave(frame * 0.04 + (-x if negate else x))
    return 1 - v if invert else v


def _radial_sweep(
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    invert: bool = False,
) -> NDArray[float32]:
    """Returns a triangle wave travelling outward from the swarm barycenter.

    Args:
        context: evaluation context for the swarm
        frame: current frame number
        invert: make the sweep dark instead of bright where it passes

    Returns:
        per-drone brightness of the sweep, in [0, 1].
    """
    relative_distances = get_centered_normalized_xy_distances(context)
    v = triangle_wave(frame * 0.05 + relative_distances)
    return 1 - v if invert else v


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
    out[:] = _axis_sweep(context, 0, frame)


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
    out[:] = _axis_sweep(context, 1, frame)


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
    out[:] = _axis_sweep(context, 2, frame)


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
    out[:] = _axis_sweep(context, 0, frame, negate=True)


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
    out[:] = _axis_sweep(context, 1, frame, negate=True)


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
    out[:] = _axis_sweep(context, 2, frame, negate=True)


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
    out[:] = _axis_sweep(context, 0, frame, invert=True)


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
    out[:] = _axis_sweep(context, 1, frame, invert=True)


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
    out[:] = _axis_sweep(context, 2, frame, invert=True)


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
    out[:] = _axis_sweep(context, 0, frame, negate=True, invert=True)


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
    out[:] = _axis_sweep(context, 1, frame, negate=True, invert=True)


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
    out[:] = _axis_sweep(context, 2, frame, negate=True, invert=True)


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
    out[:] = _radial_sweep(context, frame)


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
    out[:] = _radial_sweep(context, frame, invert=True)


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
    out[:] = steepen(_radial_sweep(context, frame))


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
    out[:] = steepen(_radial_sweep(context, frame, invert=True))
