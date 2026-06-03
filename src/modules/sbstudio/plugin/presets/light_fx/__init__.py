"""Built-in light effect output presets for Skybrush Studio.

Functions are referenced by a stable string ID, so projects stay portable
across machines and operating systems (no .py file paths inside .blend).

A preset function returns a float in ``[0, 1]`` for the X/Y axis of the
color ramp / image lookup, given:

    def my_preset(frame, time_fraction, drone_index, formation_index,
                  position, drone_count) -> float: ...

Display names follow the format ``<circled-number><human-readable name>``,
e.g. ``①Odd-Even Pulse`` (English) / ``①奇偶脉冲`` (Chinese). The number is
assigned by registration order across all categories.

CRITICAL: Per the Blender Python API docs, the items list returned from an
``EnumProperty`` ``items=`` callback MUST keep its strings alive for as long
as the EnumProperty is registered, otherwise Blender will read freed memory
and crash / hang (very visible on macOS).  We therefore build the items list
ONCE at module load time and store it in ``_CACHED_ENUM_ITEMS``; the
callback returns that single list reference forever.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

__all__ = (
    "PresetMeta",
    "PRESETS",
    "register_preset",
    "get_preset_function",
    "get_preset_enum_items",
    "register",
    "unregister",
)


# ---------------------------------------------------------------------------
# Registry types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PresetMeta:
    id: str
    label: str  # English label (used as the i18n source string)
    label_zh: str  # Chinese label (registered as zh_HANS translation)
    label_ja: str  # Japanese label (registered as ja_JP translation)
    function: Callable[..., float]
    description: str = ""
    aliases: tuple[str, ...] = field(default_factory=tuple)


# Insertion-ordered.  Order here = order in the UI dropdown = circled number.
PRESETS: dict[str, PresetMeta] = {}


def register_preset(
    *,
    id: str,
    label: str,
    label_zh: str,
    label_ja: str = "",
    description: str = "",
    aliases: tuple[str, ...] = (),
):
    def decorator(fn: Callable[..., float]) -> Callable[..., float]:
        if id in PRESETS:
            raise ValueError(f"Duplicate light-fx preset id: {id!r}")
        PRESETS[id] = PresetMeta(
            id=id,
            label=label,
            label_zh=label_zh,
            label_ja=label_ja or label,
            function=fn,
            description=description,
            aliases=aliases,
        )
        return fn

    return decorator


def get_preset_function(preset_id: str) -> Callable[..., float] | None:
    meta = PRESETS.get(preset_id)
    return meta.function if meta is not None else None


# ---------------------------------------------------------------------------
# Built-in presets.  Each function returns a float in [0, 1].
# Order here defines the numbering ①, ②, ③, ...
# ---------------------------------------------------------------------------


# ============================ basic ============================


@register_preset(
    id="odd_even_pulse",
    label="Odd-Even Pulse",
    label_zh="奇偶脉冲",
    label_ja="奇数偶数パルス",
    aliases=("奇偶脉冲", "odd_even_pulse"),
)
def odd_even_pulse(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    is_odd = (formation_index or 0) % 2
    return (math.sin(frame * 0.1 + is_odd * math.pi) + 1) / 2


@register_preset(
    id="odd_even_constant",
    label="Odd-Even Constant",
    label_zh="奇偶恒亮",
    label_ja="奇数偶数定常",
    aliases=("奇偶恒亮", "odd_even_brightness"),
)
def odd_even_constant(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    is_odd = (formation_index or 0) % 2
    return 1.0 if is_odd else 0.5


@register_preset(
    id="simple_filling",
    label="Simple Gradient Fill",
    label_zh="简单渐亮",
    label_ja="シンプルグラデーション",
    aliases=("简单渐亮", "simple_filling"),
)
def simple_filling(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    if not drone_count:
        return 0.0
    factor = (formation_index or 0) / drone_count
    return factor * time_fraction


# ============================ filling ============================


def _continuous_filling(frame, formation_index, drone_count, speed_factor, divisor):
    if not drone_count:
        return 0.0
    wave_length = max(drone_count / divisor, 1e-6)
    fi = formation_index or 0
    offset = (fi % wave_length) / wave_length
    return (math.sin((frame * 0.1 * speed_factor) + offset * 2 * math.pi) + 1) / 2


@register_preset(
    id="clover_fill",
    label="Clover Fill",
    label_zh="三叶草填充",
    label_ja="クローバーフィル",
    aliases=("三叶草填充", "continuous_fillingCLOVER"),
)
def clover_fill(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _continuous_filling(frame, formation_index, drone_count, 0.6, 3)


@register_preset(
    id="continuous_filling_1",
    label="Continuous Filling 1",
    label_zh="连续填充1",
    label_ja="連続フィル1",
    aliases=("连续填充1", "continuous_filling1"),
)
def continuous_filling_1(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _continuous_filling(frame, formation_index, drone_count, 1.0, 3)


@register_preset(
    id="continuous_filling_1_5",
    label="Continuous Filling 1.5",
    label_zh="连续填充1.5",
    label_ja="連続フィル1.5",
    aliases=("连续填充1p5", "continuous_filling1p5"),
)
def continuous_filling_1_5(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _continuous_filling(frame, formation_index, drone_count, 1.5, 10)


@register_preset(
    id="continuous_filling_2",
    label="Continuous Filling 2",
    label_zh="连续填充2",
    label_ja="連続フィル2",
    aliases=("连续填充2", "continuous_filling2"),
)
def continuous_filling_2(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _continuous_filling(frame, formation_index, drone_count, 2.0, 5)


@register_preset(
    id="continuous_filling_3",
    label="Continuous Filling 3",
    label_zh="连续填充3",
    label_ja="連続フィル3",
    aliases=("连续填充3", "continuous_filling3"),
)
def continuous_filling_3(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _continuous_filling(frame, formation_index, drone_count, 3.0, 5)


@register_preset(
    id="continuous_filling_4",
    label="Continuous Filling 4",
    label_zh="连续填充4",
    label_ja="連続フィル4",
    aliases=("连续填充4", "continuous_filling4"),
)
def continuous_filling_4(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _continuous_filling(frame, formation_index, drone_count, 4.0, 5)


@register_preset(
    id="continuous_filling_5",
    label="Continuous Filling 5",
    label_zh="连续填充5",
    label_ja="連続フィル5",
    aliases=("连续填充5", "continuous_filling5"),
)
def continuous_filling_5(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _continuous_filling(frame, formation_index, drone_count, 5.0, 5)


@register_preset(
    id="continuous_filling_stripes",
    label="Continuous Stripes",
    label_zh="连续条纹填充",
    label_ja="連続ストライプ",
    aliases=("连续条纹填充", "continuous_fillingstripes"),
)
def continuous_filling_stripes(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _continuous_filling(frame, formation_index, drone_count, 1.0, 5)


# ============================ ramp / wave ============================


@register_preset(
    id="ramp_down_wave",
    label="Ramp-Down Wave",
    label_zh="递减坡形波",
    label_ja="ランプダウン波",
    aliases=("递减坡形波", "ramp_down_wave"),
)
def ramp_down_wave(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    wave_length = 50
    return 1 - ((frame + (formation_index or 0)) % wave_length / wave_length)


def _ramp_up(frame, formation_index, wave_length):
    return (frame + (formation_index or 0)) % wave_length / wave_length


@register_preset(
    id="ramp_up_wave_10",
    label="Ramp-Up Wave 10",
    label_zh="递增坡形波10",
    label_ja="ランプアップ波10",
    aliases=("递增坡形波10", "ramp_up_wave10"),
)
def ramp_up_wave_10(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _ramp_up(frame, formation_index, 10)


@register_preset(
    id="ramp_up_wave_15",
    label="Ramp-Up Wave 15",
    label_zh="递增坡形波15",
    label_ja="ランプアップ波15",
    aliases=("递增坡形波15", "ramp_up_wave15"),
)
def ramp_up_wave_15(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _ramp_up(frame, formation_index, 15)


@register_preset(
    id="ramp_up_wave_25",
    label="Ramp-Up Wave 25",
    label_zh="递增坡形波25",
    label_ja="ランプアップ波25",
    aliases=("递增坡形波25", "ramp_up_wave25"),
)
def ramp_up_wave_25(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _ramp_up(frame, formation_index, 25)


@register_preset(
    id="ramp_up_wave_75",
    label="Ramp-Up Wave 75",
    label_zh="递增坡形波75",
    label_ja="ランプアップ波75",
    aliases=("递增坡形波75", "ramp_up_wave75"),
)
def ramp_up_wave_75(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _ramp_up(frame, formation_index, 75)


@register_preset(
    id="ramp_up_wave_100",
    label="Ramp-Up Wave 100",
    label_zh="递增坡形波100",
    label_ja="ランプアップ波100",
    aliases=("递增坡形波100", "ramp_up_wave100"),
)
def ramp_up_wave_100(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _ramp_up(frame, formation_index, 100)


@register_preset(
    id="ramp_up_wave_150",
    label="Ramp-Up Wave 150",
    label_zh="递增坡形波150",
    label_ja="ランプアップ波150",
    aliases=("递增坡形波150", "ramp_up_wave150"),
)
def ramp_up_wave_150(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _ramp_up(frame, formation_index, 150)


@register_preset(
    id="triangle_wave",
    label="Triangle Wave",
    label_zh="三角波",
    label_ja="三角波",
    aliases=("三角波", "triangle_wave"),
)
def triangle_wave(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    wave_length = 50
    offset = (frame + (formation_index or 0)) % wave_length / wave_length
    return 1 - abs(2 * offset - 1)


# ============================ pulse ============================


@register_preset(
    id="expanding_pulse",
    label="Expanding Pulse",
    label_zh="扩散脉冲",
    label_ja="拡散パルス",
    aliases=("扩散脉冲", "expanding_pulse"),
)
def expanding_pulse(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    fi = formation_index or 0
    pulse_center = drone_count // 1 if drone_count else 0
    distance_from_center = abs(fi - pulse_center)
    pulse = (math.sin(frame * 0.1 - distance_from_center * 0.01) + 0.5) / 2
    # Clamp into [0, 1] (the original returned [-0.25, 0.75])
    return max(0.0, min(1.0, pulse))


@register_preset(
    id="wave_effect",
    label="Spatial Wave",
    label_zh="空间波纹",
    label_ja="空間波",
    description="Sinusoidal wave traveling along the world X axis",
    aliases=("空间波纹", "wave_effect"),
)
def wave_effect(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    speed = 0.1
    distance = position[0] if position is not None else 0.0
    return (math.sin(frame * speed - distance) + 1) / 2


# ============================ grouping ============================


def _ranges_lookup(ranges, formation_index):
    fi = formation_index or 0
    for start, end, brightness in ranges:
        if start <= fi <= end:
            return brightness
    return 0.0


@register_preset(
    id="group_ranges_3",
    label="3 Group Ranges",
    label_zh="三段亮度分区",
    label_ja="3グループ範囲",
    description="Hard-coded 3-band brightness mapping by formation index",
    aliases=("三段亮度分区", "LightFx3group_color_ranges"),
)
def group_ranges_3(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    ranges = [
        (0, 17, 0.1),
        (18, 35, 0.2),
        (36, 53, 0.4),
        (54, 71, 0.3),
        (72, 99, 0.5),
    ]
    return _ranges_lookup(ranges, formation_index)


@register_preset(
    id="group_ranges_5",
    label="5 Group Ranges",
    label_zh="五段亮度分区",
    label_ja="5グループ範囲",
    description="Hard-coded 5-band brightness mapping by formation index",
    aliases=("五段亮度分区", "LightFx5group_color_ranges"),
)
def group_ranges_5(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    ranges = [
        (0, 19, 0.2),
        (20, 39, 0.1),
        (36, 53, 0.4),
        (54, 71, 0.3),
        (72, 99, 0.5),
    ]
    return _ranges_lookup(ranges, formation_index)


# ============================ numbered ============================


@register_preset(
    id="lightfx_0",
    label="Light FX 0",
    label_zh="灯效0",
    label_ja="ライトFX 0",
    aliases=("灯效0", "LightFX0"),
)
def lightfx_0(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    if not drone_count:
        return 0.0
    speed_factor = 1.0
    wave_length = max(drone_count / 25, 1e-6)
    offset = ((formation_index or 0) % wave_length) / wave_length
    return (math.sin((frame * 0.13 * speed_factor) + offset * 3 * math.pi) + 1) / 2


@register_preset(
    id="lightfx_1",
    label="Light FX 1",
    label_zh="灯效1",
    label_ja="ライトFX 1",
    aliases=("灯效1", "LightFX1"),
)
def lightfx_1(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    if not drone_count:
        return 0.0
    speed_factor = 1.0
    wave_length = max(drone_count / 5, 1e-6)
    offset = ((formation_index or 0) % wave_length) / wave_length
    return (math.sin((frame * 0.13 * speed_factor) + offset * 3 * math.pi) + 1) / 2


@register_preset(
    id="lightfx_4",
    label="Light FX 4",
    label_zh="灯效4",
    label_ja="ライトFX 4",
    aliases=("灯效4", "LightFx4"),
)
def lightfx_4(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    is_odd = (formation_index or 0) % 2
    return (math.sin(frame * 0.2 + is_odd * math.pi) + 1) / 4


@register_preset(
    id="lightfx_6",
    label="Light FX 6",
    label_zh="灯效6",
    label_ja="ライトFX 6",
    aliases=("灯效6", "LightFx6"),
)
def lightfx_6(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    wave_length = 50
    return (frame + (formation_index or 0)) % wave_length / wave_length


@register_preset(
    id="lightfx_7",
    label="Light FX 7",
    label_zh="灯效7",
    label_ja="ライトFX 7",
    aliases=("灯效7", "LightFx7"),
)
def lightfx_7(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    wave_length = 400
    offset = (frame + (formation_index or 0)) % wave_length / wave_length
    return 1 - abs(2 * offset - 1)


@register_preset(
    id="lightfx_8",
    label="Light FX 8",
    label_zh="灯效8",
    label_ja="ライトFX 8",
    aliases=("灯效8", "LightFx8"),
)
def lightfx_8(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    if not drone_count:
        return 0.0
    speed_factor = -0.2
    wave_length = max(drone_count / 1, 1e-6)
    offset = ((formation_index or 0) % wave_length) / wave_length
    return (math.sin((frame * 0.1 * speed_factor) + offset * 1.5 * math.pi) + 1) / 2


# ============================ v5.1 custom effects ============================


# 1. Radial Diffusion (径向扩散) - 3 presets
@register_preset(
    id="radial_diffusion_xy",
    label="Radial Diffusion XY",
    label_zh="径向扩散_XY",
    label_ja="放射拡散_XY",
    aliases=("径向扩散_XY",),
)
def radial_diffusion_xy(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    distance = _v51_get_plane_distance(position, "XY")
    return (math.sin(frame * _V51_RADIAL_SPEED - distance * _V51_RADIAL_WAVE_K) + 1) / 2


@register_preset(
    id="radial_diffusion_xz",
    label="Radial Diffusion XZ",
    label_zh="径向扩散_XZ",
    label_ja="放射拡散_XZ",
    aliases=("径向扩散_XZ",),
)
def radial_diffusion_xz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    distance = _v51_get_plane_distance(position, "XZ")
    return (math.sin(frame * _V51_RADIAL_SPEED - distance * _V51_RADIAL_WAVE_K) + 1) / 2


@register_preset(
    id="radial_diffusion_yz",
    label="Radial Diffusion YZ",
    label_zh="径向扩散_YZ",
    label_ja="放射拡散_YZ",
    aliases=("径向扩散_YZ",),
)
def radial_diffusion_yz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    distance = _v51_get_plane_distance(position, "YZ")
    return (math.sin(frame * _V51_RADIAL_SPEED - distance * _V51_RADIAL_WAVE_K) + 1) / 2


# 2. Radial Convergence (径向汇聚) - 3 presets
@register_preset(
    id="radial_convergence_xy",
    label="Radial Convergence XY",
    label_zh="径向汇聚_XY",
    label_ja="放射収束_XY",
    aliases=("径向汇聚_XY",),
)
def radial_convergence_xy(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    distance = _v51_get_plane_distance(position, "XY")
    return (math.sin(frame * _V51_RADIAL_SPEED + distance * _V51_RADIAL_WAVE_K) + 1) / 2


@register_preset(
    id="radial_convergence_xz",
    label="Radial Convergence XZ",
    label_zh="径向汇聚_XZ",
    label_ja="放射収束_XZ",
    aliases=("径向汇聚_XZ",),
)
def radial_convergence_xz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    distance = _v51_get_plane_distance(position, "XZ")
    return (math.sin(frame * _V51_RADIAL_SPEED + distance * _V51_RADIAL_WAVE_K) + 1) / 2


@register_preset(
    id="radial_convergence_yz",
    label="Radial Convergence YZ",
    label_zh="径向汇聚_YZ",
    label_ja="放射収束_YZ",
    aliases=("径向汇聚_YZ",),
)
def radial_convergence_yz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    distance = _v51_get_plane_distance(position, "YZ")
    return (math.sin(frame * _V51_RADIAL_SPEED + distance * _V51_RADIAL_WAVE_K) + 1) / 2


# 3. Roundtrip Sweep (往返扫光) - 6 presets
@register_preset(
    id="roundtrip_sweep_ltr_xy",
    label="Roundtrip Sweep L→R XY",
    label_zh="往返扫光_左到右_XY",
    label_ja="往復スイープ_左→右_XY",
    aliases=("往返扫光_左到右_XY",),
)
def roundtrip_sweep_ltr_xy(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    coord = _v51_get_axis_coord(position, "X")
    return _v51_gradient_sweep_roundtrip(coord, +1, frame)


@register_preset(
    id="roundtrip_sweep_rtl_xy",
    label="Roundtrip Sweep R→L XY",
    label_zh="往返扫光_右到左_XY",
    label_ja="往復スイープ_右→左_XY",
    aliases=("往返扫光_右到左_XY",),
)
def roundtrip_sweep_rtl_xy(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    coord = _v51_get_axis_coord(position, "X")
    return _v51_gradient_sweep_roundtrip(coord, -1, frame)


@register_preset(
    id="roundtrip_sweep_ltr_xz",
    label="Roundtrip Sweep L→R XZ",
    label_zh="往返扫光_左到右_XZ",
    label_ja="往復スイープ_左→右_XZ",
    aliases=("往返扫光_左到右_XZ",),
)
def roundtrip_sweep_ltr_xz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    coord = _v51_get_axis_coord(position, "X")
    return _v51_gradient_sweep_roundtrip(coord, +1, frame)


@register_preset(
    id="roundtrip_sweep_rtl_xz",
    label="Roundtrip Sweep R→L XZ",
    label_zh="往返扫光_右到左_XZ",
    label_ja="往復スイープ_右→左_XZ",
    aliases=("往返扫光_右到左_XZ",),
)
def roundtrip_sweep_rtl_xz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    coord = _v51_get_axis_coord(position, "X")
    return _v51_gradient_sweep_roundtrip(coord, -1, frame)


@register_preset(
    id="roundtrip_sweep_ltr_yz",
    label="Roundtrip Sweep L→R YZ",
    label_zh="往返扫光_左到右_YZ",
    label_ja="往復スイープ_左→右_YZ",
    aliases=("往返扫光_左到右_YZ",),
)
def roundtrip_sweep_ltr_yz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    coord = _v51_get_axis_coord(position, "Y")
    return _v51_gradient_sweep_roundtrip(coord, +1, frame)


@register_preset(
    id="roundtrip_sweep_rtl_yz",
    label="Roundtrip Sweep R→L YZ",
    label_zh="往返扫光_右到左_YZ",
    label_ja="往復スイープ_右→左_YZ",
    aliases=("往返扫光_右到左_YZ",),
)
def roundtrip_sweep_rtl_yz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    coord = _v51_get_axis_coord(position, "Y")
    return _v51_gradient_sweep_roundtrip(coord, -1, frame)


# 4. Oneway Sweep (单向扫光) - 6 presets
@register_preset(
    id="oneway_sweep_ltr_xy",
    label="Oneway Sweep L→R XY",
    label_zh="单向扫光_左到右_XY",
    label_ja="片道スイープ_左→右_XY",
    aliases=("单向扫光_左到右_XY",),
)
def oneway_sweep_ltr_xy(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    coord = _v51_get_axis_coord(position, "X")
    return _v51_gradient_sweep_oneway_loop(coord, +1, frame)


@register_preset(
    id="oneway_sweep_rtl_xy",
    label="Oneway Sweep R→L XY",
    label_zh="单向扫光_右到左_XY",
    label_ja="片道スイープ_右→左_XY",
    aliases=("单向扫光_右到左_XY",),
)
def oneway_sweep_rtl_xy(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    coord = _v51_get_axis_coord(position, "X")
    return _v51_gradient_sweep_oneway_loop(coord, -1, frame)


@register_preset(
    id="oneway_sweep_ltr_xz",
    label="Oneway Sweep L→R XZ",
    label_zh="单向扫光_左到右_XZ",
    label_ja="片道スイープ_左→右_XZ",
    aliases=("单向扫光_左到右_XZ",),
)
def oneway_sweep_ltr_xz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    coord = _v51_get_axis_coord(position, "X")
    return _v51_gradient_sweep_oneway_loop(coord, +1, frame)


@register_preset(
    id="oneway_sweep_rtl_xz",
    label="Oneway Sweep R→L XZ",
    label_zh="单向扫光_右到左_XZ",
    label_ja="片道スイープ_右→左_XZ",
    aliases=("单向扫光_右到左_XZ",),
)
def oneway_sweep_rtl_xz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    coord = _v51_get_axis_coord(position, "X")
    return _v51_gradient_sweep_oneway_loop(coord, -1, frame)


@register_preset(
    id="oneway_sweep_ltr_yz",
    label="Oneway Sweep L→R YZ",
    label_zh="单向扫光_左到右_YZ",
    label_ja="片道スイープ_左→右_YZ",
    aliases=("单向扫光_左到右_YZ",),
)
def oneway_sweep_ltr_yz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    coord = _v51_get_axis_coord(position, "Y")
    return _v51_gradient_sweep_oneway_loop(coord, +1, frame)


@register_preset(
    id="oneway_sweep_rtl_yz",
    label="Oneway Sweep R→L YZ",
    label_zh="单向扫光_右到左_YZ",
    label_ja="片道スイープ_右→左_YZ",
    aliases=("单向扫光_右到左_YZ",),
)
def oneway_sweep_rtl_yz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    coord = _v51_get_axis_coord(position, "Y")
    return _v51_gradient_sweep_oneway_loop(coord, -1, frame)


# 5. Diagonal Sweep (倾斜扫光) - 6 presets
@register_preset(
    id="diagonal_sweep_lb_rt_xy",
    label="Diagonal Sweep LB→RT XY",
    label_zh="倾斜扫光_左下到右上_XY",
    label_ja="斜めスイープ_左下→右上_XY",
    aliases=("倾斜扫光_左下到右上_XY",),
)
def diagonal_sweep_lb_rt_xy(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    pos_a = _v51_get_axis_coord(position, "X")
    pos_b = _v51_get_axis_coord(position, "Y")
    return _v51_gradient_sweep_diagonal(pos_a, pos_b, +1, frame)


@register_preset(
    id="diagonal_sweep_rt_lb_xy",
    label="Diagonal Sweep RT→LB XY",
    label_zh="倾斜扫光_右上到左下_XY",
    label_ja="斜めスイープ_右上→左下_XY",
    aliases=("倾斜扫光_右上到左下_XY",),
)
def diagonal_sweep_rt_lb_xy(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    pos_a = _v51_get_axis_coord(position, "X")
    pos_b = _v51_get_axis_coord(position, "Y")
    return _v51_gradient_sweep_diagonal(pos_a, pos_b, -1, frame)


@register_preset(
    id="diagonal_sweep_lb_rt_xz",
    label="Diagonal Sweep LB→RT XZ",
    label_zh="倾斜扫光_左下到右上_XZ",
    label_ja="斜めスイープ_左下→右上_XZ",
    aliases=("倾斜扫光_左下到右上_XZ",),
)
def diagonal_sweep_lb_rt_xz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    pos_a = _v51_get_axis_coord(position, "X")
    pos_b = _v51_get_axis_coord(position, "Z")
    return _v51_gradient_sweep_diagonal(pos_a, pos_b, +1, frame)


@register_preset(
    id="diagonal_sweep_rt_lb_xz",
    label="Diagonal Sweep RT→LB XZ",
    label_zh="倾斜扫光_右上到左下_XZ",
    label_ja="斜めスイープ_右上→左下_XZ",
    aliases=("倾斜扫光_右上到左下_XZ",),
)
def diagonal_sweep_rt_lb_xz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    pos_a = _v51_get_axis_coord(position, "X")
    pos_b = _v51_get_axis_coord(position, "Z")
    return _v51_gradient_sweep_diagonal(pos_a, pos_b, -1, frame)


@register_preset(
    id="diagonal_sweep_lb_rt_yz",
    label="Diagonal Sweep LB→RT YZ",
    label_zh="倾斜扫光_左下到右上_YZ",
    label_ja="斜めスイープ_左下→右上_YZ",
    aliases=("倾斜扫光_左下到右上_YZ",),
)
def diagonal_sweep_lb_rt_yz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    pos_a = _v51_get_axis_coord(position, "Y")
    pos_b = _v51_get_axis_coord(position, "Z")
    return _v51_gradient_sweep_diagonal(pos_a, pos_b, +1, frame)


@register_preset(
    id="diagonal_sweep_rt_lb_yz",
    label="Diagonal Sweep RT→LB YZ",
    label_zh="倾斜扫光_右上到左下_YZ",
    label_ja="斜めスイープ_右上→左下_YZ",
    aliases=("倾斜扫光_右上到左下_YZ",),
)
def diagonal_sweep_rt_lb_yz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    pos_a = _v51_get_axis_coord(position, "Y")
    pos_b = _v51_get_axis_coord(position, "Z")
    return _v51_gradient_sweep_diagonal(pos_a, pos_b, -1, frame)


# 6. Chasing Tails (追逐尾巴) - 3 presets
@register_preset(
    id="chasing_tails_xy",
    label="Chasing Tails XY",
    label_zh="追逐尾巴_XY",
    label_ja="追跡_XY",
    aliases=("追逐尾巴_XY",),
)
def chasing_tails_xy(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _v51_chasing_tails_core(position, "XY", frame, formation_index)


@register_preset(
    id="chasing_tails_xz",
    label="Chasing Tails XZ",
    label_zh="追逐尾巴_XZ",
    label_ja="追跡_XZ",
    aliases=("追逐尾巴_XZ",),
)
def chasing_tails_xz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _v51_chasing_tails_core(position, "XZ", frame, formation_index)


@register_preset(
    id="chasing_tails_yz",
    label="Chasing Tails YZ",
    label_zh="追逐尾巴_YZ",
    label_ja="追跡_YZ",
    aliases=("追逐尾巴_YZ",),
)
def chasing_tails_yz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _v51_chasing_tails_core(position, "YZ", frame, formation_index)


# 7. Radar Scan (雷达扫描) - 9 presets
@register_preset(
    id="radar_scan_60_xy",
    label="Radar Scan 60° XY",
    label_zh="雷达扫描_60度_XY",
    label_ja="レーダースキャン_60°_XY",
    aliases=("雷达扫描_60度_XY",),
)
def radar_scan_60_xy(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _v51_radar_scan_core(position, "XY", 60.0, frame)


@register_preset(
    id="radar_scan_90_xy",
    label="Radar Scan 90° XY",
    label_zh="雷达扫描_90度_XY",
    label_ja="レーダースキャン_90°_XY",
    aliases=("雷达扫描_90度_XY",),
)
def radar_scan_90_xy(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _v51_radar_scan_core(position, "XY", 90.0, frame)


@register_preset(
    id="radar_scan_120_xy",
    label="Radar Scan 120° XY",
    label_zh="雷达扫描_120度_XY",
    label_ja="レーダースキャン_120°_XY",
    aliases=("雷达扫描_120度_XY",),
)
def radar_scan_120_xy(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _v51_radar_scan_core(position, "XY", 120.0, frame)


@register_preset(
    id="radar_scan_60_xz",
    label="Radar Scan 60° XZ",
    label_zh="雷达扫描_60度_XZ",
    label_ja="レーダースキャン_60°_XZ",
    aliases=("雷达扫描_60度_XZ",),
)
def radar_scan_60_xz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _v51_radar_scan_core(position, "XZ", 60.0, frame)


@register_preset(
    id="radar_scan_90_xz",
    label="Radar Scan 90° XZ",
    label_zh="雷达扫描_90度_XZ",
    label_ja="レーダースキャン_90°_XZ",
    aliases=("雷达扫描_90度_XZ",),
)
def radar_scan_90_xz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _v51_radar_scan_core(position, "XZ", 90.0, frame)


@register_preset(
    id="radar_scan_120_xz",
    label="Radar Scan 120° XZ",
    label_zh="雷达扫描_120度_XZ",
    label_ja="レーダースキャン_120°_XZ",
    aliases=("雷达扫描_120度_XZ",),
)
def radar_scan_120_xz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _v51_radar_scan_core(position, "XZ", 120.0, frame)


@register_preset(
    id="radar_scan_60_yz",
    label="Radar Scan 60° YZ",
    label_zh="雷达扫描_60度_YZ",
    label_ja="レーダースキャン_60°_YZ",
    aliases=("雷达扫描_60度_YZ",),
)
def radar_scan_60_yz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _v51_radar_scan_core(position, "YZ", 60.0, frame)


@register_preset(
    id="radar_scan_90_yz",
    label="Radar Scan 90° YZ",
    label_zh="雷达扫描_90度_YZ",
    label_ja="レーダースキャン_90°_YZ",
    aliases=("雷达扫描_90度_YZ",),
)
def radar_scan_90_yz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _v51_radar_scan_core(position, "YZ", 90.0, frame)


@register_preset(
    id="radar_scan_120_yz",
    label="Radar Scan 120° YZ",
    label_zh="雷达扫描_120度_YZ",
    label_ja="レーダースキャン_120°_YZ",
    aliases=("雷达扫描_120度_YZ",),
)
def radar_scan_120_yz(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _v51_radar_scan_core(position, "YZ", 120.0, frame)


# 8. Pattern Paint-On (图案逐渐点亮) - 1 preset (only XY works)
@register_preset(
    id="pattern_paint_on_xy",
    label="Pattern Paint-On XY",
    label_zh="图案逐渐点亮_XY",
    label_ja="パターンペイント_XY",
    aliases=("图案逐渐点亮_XY",),
)
def pattern_paint_on_xy(
    frame, time_fraction, drone_index, formation_index, position, drone_count
):
    return _v51_paint_on_core(position, "XY", frame)


# Global parameters for v5.1 effects
_V51_RADIAL_SPEED = 0.10
_V51_RADIAL_WAVE_K = 0.30
_V51_SWEEP_RANGE_MIN = -30.0
_V51_SWEEP_RANGE_MAX = 30.0
_V51_SWEEP_ONEWAY_DURATION = 120
_V51_SWEEP_ONEWAY_PAUSE = 48
_V51_SWEEP_ROUNDTRIP_PAUSE = 24
_V51_SWEEP_GRADIENT_WIDTH = 8.0
_V51_CHASE_SPEED = 0.12
_V51_CHASE_SPATIAL_K = 0.1
_V51_RADAR_ANGULAR_SPEED = 2400.0 / 34.0
_V51_RADAR_FRAMERATE = 24.0
_V51_PAINT_DURATION_FRAMES = 120
_V51_PAINT_FRAMERATE = 24.0


# Helper functions for v5.1 effects
def _v51_get_plane_distance(position, plane: str):
    if position is None:
        return 0.0
    x, y, z = position
    coords = {"X": x, "Y": y, "Z": z}
    a, b = plane.upper()
    return math.sqrt(coords[a] ** 2 + coords[b] ** 2)


def _v51_get_axis_coord(position, axis: str):
    if position is None:
        return 0.0
    coords = {"X": position[0], "Y": position[1], "Z": position[2]}
    return coords[axis.upper()]


def _v51_get_plane_coords(position, plane: str):
    if position is None:
        return (0.0, 0.0)
    x, y, z = position
    coords = {"X": x, "Y": y, "Z": z}
    a, b = plane.upper()
    return (coords[a], coords[b])


def _v51_gradient_sweep_roundtrip(coord: float, direction: int, frame: int):
    oneway_frames = _V51_SWEEP_ONEWAY_DURATION
    pause_frames = _V51_SWEEP_ROUNDTRIP_PAUSE
    full_cycle = 2 * (oneway_frames + pause_frames)
    t = frame % full_cycle
    if t < oneway_frames:
        phase = t / max(oneway_frames, 1)
    elif t < oneway_frames + pause_frames:
        phase = 1.0
    elif t < 2 * oneway_frames + pause_frames:
        phase = 1.0 - (t - oneway_frames - pause_frames) / max(oneway_frames, 1)
    else:
        phase = 0.0
    sweep_pos = _V51_SWEEP_RANGE_MIN + phase * (
        _V51_SWEEP_RANGE_MAX - _V51_SWEEP_RANGE_MIN
    )
    if direction < 0:
        sweep_pos = _V51_SWEEP_RANGE_MAX - (sweep_pos - _V51_SWEEP_RANGE_MIN)
    dist = abs(coord - sweep_pos)
    half_width = _V51_SWEEP_GRADIENT_WIDTH / 2.0
    if dist >= half_width:
        return 0.0
    brightness = 1.0 - (dist / half_width)
    return max(0.0, min(1.0, brightness))


def _v51_gradient_sweep_oneway_loop(coord: float, direction: int, frame: int):
    oneway_frames = _V51_SWEEP_ONEWAY_DURATION
    pause_frames = _V51_SWEEP_ONEWAY_PAUSE
    full_cycle = oneway_frames + pause_frames
    t = frame % full_cycle
    if t < oneway_frames:
        phase = t / max(oneway_frames, 1)
    else:
        return 0.0
    if direction > 0:
        sweep_pos = _V51_SWEEP_RANGE_MIN + phase * (
            _V51_SWEEP_RANGE_MAX - _V51_SWEEP_RANGE_MIN
        )
    else:
        sweep_pos = _V51_SWEEP_RANGE_MAX - phase * (
            _V51_SWEEP_RANGE_MAX - _V51_SWEEP_RANGE_MIN
        )
    dist = abs(coord - sweep_pos)
    half_width = _V51_SWEEP_GRADIENT_WIDTH / 2.0
    if dist >= half_width:
        return 0.0
    brightness = 1.0 - (dist / half_width)
    return max(0.0, min(1.0, brightness))


def _v51_gradient_sweep_diagonal(
    pos_a: float, pos_b: float, direction: int, frame: int
):
    proj = (pos_a + pos_b) / math.sqrt(2)
    oneway_frames = _V51_SWEEP_ONEWAY_DURATION
    pause_frames = _V51_SWEEP_ONEWAY_PAUSE
    full_cycle = oneway_frames + pause_frames
    t = frame % full_cycle
    if t < oneway_frames:
        phase = t / max(oneway_frames, 1)
    else:
        return 0.0
    if direction > 0:
        sweep_pos = _V51_SWEEP_RANGE_MIN + phase * (
            _V51_SWEEP_RANGE_MAX - _V51_SWEEP_RANGE_MIN
        )
    else:
        sweep_pos = _V51_SWEEP_RANGE_MAX - phase * (
            _V51_SWEEP_RANGE_MAX - _V51_SWEEP_RANGE_MIN
        )
    dist = abs(proj - sweep_pos)
    half_width = _V51_SWEEP_GRADIENT_WIDTH / 2.0
    if dist >= half_width:
        return 0.0
    brightness = 1.0 - (dist / half_width)
    return max(0.0, min(1.0, brightness))


def _v51_chasing_tails_core(position, plane: str, frame: int, formation_index):
    if position is None:
        coord = 0.0
    else:
        axis = plane[0].upper()
        coords_map = {"X": position[0], "Y": position[1], "Z": position[2]}
        coord = coords_map[axis]
    fi = formation_index if formation_index is not None else 0
    group = fi % 2
    travel_phase = frame * _V51_CHASE_SPEED - coord * _V51_CHASE_SPATIAL_K
    if group == 0:
        v = math.sin(travel_phase)
    else:
        v = math.cos(travel_phase)
    return (v + 1) / 2


def _v51_radar_scan_core(position, plane: str, fan_angle_deg: float, frame: int):
    coord_a, coord_b = _v51_get_plane_coords(position, plane)
    time_sec = frame / _V51_RADAR_FRAMERATE
    rotation_angle_deg = (time_sec * _V51_RADAR_ANGULAR_SPEED) % 360.0
    drone_angle_deg = math.degrees(math.atan2(coord_b, coord_a))
    if drone_angle_deg < 0:
        drone_angle_deg += 360.0
    fan_start = rotation_angle_deg
    fan_end = (rotation_angle_deg + fan_angle_deg) % 360.0
    if fan_start <= fan_end:
        in_fan = fan_start <= drone_angle_deg <= fan_end
    else:
        in_fan = (drone_angle_deg >= fan_start) or (drone_angle_deg <= fan_end)
    return 1.0 if in_fan else 0.0


def _v51_paint_on_core(position, plane: str, frame: int):
    coord_a, coord_b = _v51_get_plane_coords(position, plane)
    drone_angle_deg = math.degrees(math.atan2(coord_b, coord_a))
    if drone_angle_deg < 0:
        drone_angle_deg += 360.0
    phase = min(frame / max(_V51_PAINT_DURATION_FRAMES, 1), 1.0)
    current_angle_deg = phase * 360.0
    if drone_angle_deg <= current_angle_deg:
        return 1.0
    else:
        return 0.0


# ---------------------------------------------------------------------------
# UI items list (built ONCE, kept alive at module level forever)
# ---------------------------------------------------------------------------


def _build_enum_items() -> list[tuple[str, str, str]]:
    """Build the EnumProperty items list ONCE.  The returned list (and all of
    its strings) live for the entire lifetime of the addon, which is required
    by Blender to avoid use-after-free on the C side.

    Numbering format: 「1」「2」「3」... (full-width brackets)
    Order: v5.1 custom effects first, then original effects (reversed order)
    """
    items: list[tuple[str, str, str]] = [("", "<None>", "")]

    # Reverse the order so v5.1 effects (added last) appear first
    reversed_presets = list(reversed(list(PRESETS.items())))

    for i, (_preset_id, meta) in enumerate(reversed_presets):
        # Use full-width brackets 「」 for numbering
        prefix = f"「{i + 1}」"
        display = f"{prefix}{meta.label}"
        items.append((meta.id, display, meta.description or meta.label))
    return items


# Module-level cache.  *** DO NOT *** rebuild this per call.
_CACHED_ENUM_ITEMS: list[tuple[str, str, str]] = _build_enum_items()


def get_preset_enum_items(self, context):
    """``items`` callback for the ``preset_id`` EnumProperty.

    Returns the same cached list every call.  Strings inside the list stay
    alive as long as the module is loaded, which prevents the well-known
    Blender crash / freeze caused by GC'd item strings (very visible on
    macOS in Material Preview mode)."""
    return _CACHED_ENUM_ITEMS


# ---------------------------------------------------------------------------
# Translations (registered with bpy.app.translations)
# ---------------------------------------------------------------------------


_I18N_DOMAIN = "sbstudio_light_fx_presets"


def _build_translation_dict() -> dict:
    """Build a Blender-compatible translation dict.  Maps each English source
    string used in the UI to its Chinese and Japanese translations."""
    zh: dict[tuple[str, str], str] = {}
    ja: dict[tuple[str, str], str] = {}

    # Translate the OUTPUT_ITEMS entry "Light preset"
    zh[("*", "Light preset")] = "灯光模版"
    zh[("*", "Built-in light effect preset (portable across machines)")] = (
        "内置灯效预设（跨电脑/系统可移植，不依赖 .py 文件路径）"
    )
    zh[("*", "Light Preset")] = "灯光模版"
    zh[("*", "Preset")] = "预设"

    ja[("*", "Light preset")] = "ライトプリセット"
    ja[("*", "Built-in light effect preset (portable across machines)")] = (
        "内蔵ライトエフェクトプリセット（マシン間でポータブル）"
    )
    ja[("*", "Light Preset")] = "ライトプリセット"
    ja[("*", "Preset")] = "プリセット"

    # Translate each preset's display string.
    # Display = 「N」+ English label.  We translate the whole composite source.
    # Order is reversed (v5.1 effects first)
    reversed_presets = list(reversed(list(PRESETS.items())))
    for i, (_preset_id, meta) in enumerate(reversed_presets):
        prefix = f"「{i + 1}」"
        en_display = f"{prefix}{meta.label}"
        zh_display = f"{prefix}{meta.label_zh}"
        ja_display = f"{prefix}{meta.label_ja}"
        zh[("*", en_display)] = zh_display
        ja[("*", en_display)] = ja_display

    return {"zh_HANS": zh, "zh_CN": zh, "ja_JP": ja}


def register() -> None:
    """Register translations for the built-in light effect presets.

    Called by the addon's top-level ``register()`` function.  Idempotent.
    """
    try:
        import bpy
    except ImportError:
        return  # Headless / unit-test context

    try:
        bpy.app.translations.unregister(_I18N_DOMAIN)
    except Exception:
        pass  # not previously registered

    try:
        bpy.app.translations.register(_I18N_DOMAIN, _build_translation_dict())
    except Exception as exc:
        # Translation is non-critical; log and move on so the addon still loads.
        print(f"[sbstudio.light_fx_presets] failed to register i18n: {exc}")


def unregister() -> None:
    try:
        import bpy
    except ImportError:
        return

    try:
        bpy.app.translations.unregister(_I18N_DOMAIN)
    except Exception:
        pass
