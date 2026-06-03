from __future__ import annotations

from math import pi, sin
from typing import TYPE_CHECKING

from .base import register_preset

if TYPE_CHECKING:
    from sbstudio.model.types import Coordinate3D


@register_preset(
    id="lightfx_0",
    label="Light FX 0",
    translations=(("zh", "灯效0"), ("ja", "ライトFX 0")),
)
def lightfx_0(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    if not drone_count:
        return 0.0
    speed_factor = 1.0
    wave_length = max(drone_count / 25, 1e-6)
    offset = ((formation_index or 0) % wave_length) / wave_length
    return (sin((frame * 0.13 * speed_factor) + offset * 3 * pi) + 1) / 2


@register_preset(
    id="lightfx_1",
    label="Light FX 1",
    translations=(("zh", "灯效1"), ("ja", "ライトFX 1")),
)
def lightfx_1(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    if not drone_count:
        return 0.0
    speed_factor = 1.0
    wave_length = max(drone_count / 5, 1e-6)
    offset = ((formation_index or 0) % wave_length) / wave_length
    return (sin((frame * 0.13 * speed_factor) + offset * 3 * pi) + 1) / 2


@register_preset(
    id="lightfx_4",
    label="Light FX 4",
    translations=(("zh", "灯效4"), ("ja", "ライトFX 4")),
)
def lightfx_4(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    is_odd = (formation_index or 0) % 2
    return (sin(frame * 0.2 + is_odd * pi) + 1) / 4


@register_preset(
    id="lightfx_6",
    label="Light FX 6",
    translations=(("zh", "灯效6"), ("ja", "ライトFX 6")),
)
def lightfx_6(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    wave_length = 50
    return (frame + (formation_index or 0)) % wave_length / wave_length


@register_preset(
    id="lightfx_7",
    label="Light FX 7",
    translations=(("zh", "灯效7"), ("ja", "ライトFX 7")),
)
def lightfx_7(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    wave_length = 400
    offset = (frame + (formation_index or 0)) % wave_length / wave_length
    return 1 - abs(2 * offset - 1)


@register_preset(
    id="lightfx_8",
    label="Light FX 8",
    translations=(("zh", "灯效8"), ("ja", "ライトFX 8")),
)
def lightfx_8(
    frame: int,
    time_fraction: float,
    drone_index: int,
    formation_index: int | None,
    position: Coordinate3D,
    drone_count: int,
) -> float:
    if not drone_count:
        return 0.0
    speed_factor = -0.2
    wave_length = max(drone_count / 1, 1e-6)
    offset = ((formation_index or 0) % wave_length) / wave_length
    return (sin((frame * 0.1 * speed_factor) + offset * 1.5 * pi) + 1) / 2
