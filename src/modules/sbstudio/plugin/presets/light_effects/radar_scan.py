from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import arctan2, degrees, float32, where
from numpy.typing import NDArray

from .base import register_preset
from .utils import get_formation_indices

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import (
        LightEffect,
        LightEffectEvaluationContext,
    )


def _get_fan_phase_and_width(
    positions: NDArray[float32], cx: float, cy: float, n: int
) -> tuple[NDArray[float32], float]:
    dx = positions[:, 0] - cx
    dy = positions[:, 1] - cy
    angles = degrees(arctan2(dy, dx)) % 360
    span = 360.0 / n
    half_span = span / 2
    return angles, half_span


def _is_in_fan(
    angles: NDArray[float32], center: float, half_span: float
) -> NDArray[float32]:
    diff = (angles - center) % 360
    return (diff >= 0) & (diff <= 2 * half_span)


@register_preset(
    id="radar_scan",
    label="Radar Scan",
    translations=(("zh", "雷达扫描"), ("ja", "レーダースキャン")),
)
def radar_scan(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    n = len(out)
    if n == 0:
        return
    pos = context.positions.as_array
    cx, cy, _ = context.swarm_center.as_array
    angles, half_span = _get_fan_phase_and_width(pos, cx, cy, n)
    indices = get_formation_indices(context)
    center_angle = (frame * 2) % 360
    out[:] = where(
        _is_in_fan(angles, center_angle, half_span),
        (indices % 2 + 0.5).astype(float32),
        0.0,
    )


@register_preset(
    id="radar_scan_2",
    label="Radar Scan 2",
    translations=(("zh", "雷达扫描2"), ("ja", "レーダースキャン2")),
)
def radar_scan_2(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    n = len(out)
    if n == 0:
        return
    pos = context.positions.as_array
    cx, cy, _ = context.swarm_center.as_array
    angles, half_span = _get_fan_phase_and_width(pos, cx, cy, n)
    center_angle = (-frame * 2) % 360
    out[:] = where(
        _is_in_fan(angles, center_angle, half_span),
        (n // 2 - abs(get_formation_indices(context) - n // 2)).astype(float32)
        / (n // 2),
        0.0,
    )


@register_preset(
    id="radar_scan_3",
    label="Radar Scan 3",
    translations=(("zh", "雷达扫描3"), ("ja", "レーダースキャン3")),
)
def radar_scan_3(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    n = len(out)
    if n == 0:
        return
    pos = context.positions.as_array
    cx, cy, _ = context.swarm_center.as_array
    angles, half_span = _get_fan_phase_and_width(pos, cx, cy, n)
    center_angle = (frame * 2) % 360
    fi = get_formation_indices(context)
    out[:] = where(
        _is_in_fan(angles, center_angle, half_span),
        where(fi % 3 == 0, 0.9, where(fi % 3 == 1, 0.5, 0.2)),
        0.0,
    )


@register_preset(
    id="radar_scan_4",
    label="Radar Scan 4",
    translations=(("zh", "雷达扫描4"), ("ja", "レーダースキャン4")),
)
def radar_scan_4(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    n = len(out)
    if n == 0:
        return
    pos = context.positions.as_array
    cx, cy, _ = context.swarm_center.as_array
    angles, half_span = _get_fan_phase_and_width(pos, cx, cy, n)
    center_angle = (frame * 3) % 360
    out[:] = where(
        _is_in_fan(angles, center_angle, half_span),
        0.8,
        0.0,
    )


@register_preset(
    id="radar_scan_5",
    label="Radar Scan 5",
    translations=(("zh", "雷达扫描5"), ("ja", "レーダースキャン5")),
)
def radar_scan_5(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    n = len(out)
    if n == 0:
        return
    pos = context.positions.as_array
    cx, cy, _ = context.swarm_center.as_array
    angles, half_span = _get_fan_phase_and_width(pos, cx, cy, n)
    center_angle = (-frame * 3) % 360
    out[:] = where(
        _is_in_fan(angles, center_angle, half_span),
        0.8,
        0.0,
    )


@register_preset(
    id="continuous_radar_scan_test",
    label="Continuous Radar Scan Test",
    translations=(("zh", "持续雷达扫描测试"), ("ja", "連続レーダースキャンテスト")),
)
def continuous_radar_scan_test(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    n = len(out)
    if n == 0:
        return
    pos = context.positions.as_array
    cx, cy, _ = context.swarm_center.as_array
    angles, _ = _get_fan_phase_and_width(pos, cx, cy, n)
    center_angle = (frame * 2) % 360
    diff = ((angles - center_angle + 180) % 360) - 180
    brightness = (1 - abs(diff / 30)).clip(0, 1)
    out[:] = brightness.astype(float32)


@register_preset(
    id="paint_on_test_1",
    label="Paint on Test 1",
    translations=(("zh", "飞入测试1"), ("ja", "ペイントオンテスト1")),
)
def paint_on_test_1(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    n = len(out)
    if n == 0:
        return
    fi = get_formation_indices(context)
    total_drones = n
    progress = frame / 100
    active_count = int(total_drones * min(progress, 1))
    out[:] = where(fi < active_count, 1.0, 0.0)


@register_preset(
    id="paint_on_test_2",
    label="Paint on Test 2",
    translations=(("zh", "飞入测试2"), ("ja", "ペイントオンテスト2")),
)
def paint_on_test_2(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    n = len(out)
    if n == 0:
        return
    fi = get_formation_indices(context)
    total_drones = n
    progress = frame / 100
    active_count = int(total_drones * min(progress, 1))
    out[:] = where(fi < active_count, (fi % 3 + 1) / 3.0, 0.0)


@register_preset(
    id="paint_on_test_3",
    label="Paint on Test 3",
    translations=(("zh", "飞入测试3"), ("ja", "ペイントオンテスト3")),
)
def paint_on_test_3(
    effect: LightEffect,
    context: LightEffectEvaluationContext,
    frame: int,
    *,
    out: NDArray[float32],
) -> None:
    n = len(out)
    if n == 0:
        return
    fi = get_formation_indices(context)
    total_drones = n
    out[:] = where(
        fi < int(total_drones * min(frame / 100, 1)),
        (2 - abs(fi - total_drones // 2) / (total_drones // 2)).clip(0, 1),
        0.0,
    )
