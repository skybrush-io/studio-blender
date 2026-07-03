#!/usr/bin/env python3
"""Render animated GIF previews for all built-in light effect presets.

This helper imports the built-in preset registry, evaluates each preset on a
sunflower seed layout over 125 frames at 25 FPS, and writes one GIF per
preset.

By default, GIFs are written into the current working directory as
``<preset_id>.gif``. Use ``--layout subdirs`` to instead save them as
``<output-dir>/<preset_id>/preview.gif``.

Note: the generated layout intentionally uses ``z = 0`` for every drone to
match the requested setup. As a consequence, presets that depend on the Z axis
(or the XZ / YZ planes) will look flatter / more degenerate than they would on
truly 3D formations.
"""

from __future__ import annotations

import argparse
import importlib
import math
import sys
from pathlib import Path
from typing import Any

try:
    Image = importlib.import_module("PIL.Image")
    ImageDraw = importlib.import_module("PIL.ImageDraw")
except ModuleNotFoundError as exc:
    raise SystemExit(
        "This helper requires Pillow.\n"
        "Run it with:\n"
        "  uv run --with pillow python dev/render_light_effect_preset_gifs.py\n"
        "or install Pillow into your environment."
    ) from exc


FRAME_START = 1
FRAME_END = 125
FPS = 25

DRONE_COUNT = 200
SUNFLOWER_RADIUS = 30.0  # chosen to match the sweep presets' [-30, 30] range

IMAGE_SIZE = 600
MARGIN = 56
DOT_RADIUS = 8

BACKGROUND = (10, 12, 18)
GUIDE = (34, 40, 56)
CONNECTOR_LINE = (92, 98, 110)
AXIS_MARKER = (140, 148, 166)
PROGRESS_BAR = (255, 204, 0)
PROGRESS_BAR_TRACK = (64, 58, 24)
PROGRESS_BAR_HEIGHT = 5

# False-color palette for visualizing scalar preset output.
# 0% -> black, 50% -> #0088ff, 100% -> white.
PALETTE = (
    (0.0, (0, 0, 0)),
    (0.5, (0, 136, 255)),
    (1.0, (255, 255, 255)),
)


_ADAPTIVE_PALETTE: Any = getattr(getattr(Image, "Palette", Image), "ADAPTIVE", None)
if _ADAPTIVE_PALETTE is None:
    _ADAPTIVE_PALETTE = Image.ADAPTIVE


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists() and (
            candidate / "src" / "modules"
        ).exists():
            return candidate
    raise SystemExit("Could not locate the repository root from the script location.")


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)
MODULE_ROOT = REPO_ROOT / "src" / "modules"

if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

# Importing the package root registers all built-in presets.
import sbstudio.plugin.presets.light_effects  # noqa: F401
from sbstudio.plugin.presets.light_effects.base import iter_preset_mapping


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render animated GIF previews for all built-in light effect presets."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory where GIFs will be written. Default: current working directory.",
    )
    parser.add_argument(
        "--layout",
        choices=("flat", "subdirs"),
        default="flat",
        help=(
            "`flat` saves <preset_id>.gif directly under the output directory; "
            "`subdirs` saves <output-dir>/<preset_id>/preview.gif."
        ),
    )
    parser.add_argument(
        "--draw-connector-line",
        action="store_true",
        help="Draw a thin line connecting consecutive drones. Disabled by default.",
    )
    parser.add_argument(
        "--drone-count",
        type=int,
        default=DRONE_COUNT,
        help=f"Number of drones to render. Default: {DRONE_COUNT}.",
    )
    args = parser.parse_args()
    if args.drone_count <= 0:
        parser.error("--drone-count must be a positive integer")
    return args


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def color_for_value(value: float) -> tuple[int, int, int]:
    value = clamp01(value)

    for (left_stop, left_color), (right_stop, right_color) in zip(PALETTE, PALETTE[1:]):
        if value <= right_stop:
            span = max(right_stop - left_stop, 1e-9)
            t = (value - left_stop) / span
            return (
                lerp(left_color[0], right_color[0], t),
                lerp(left_color[1], right_color[1], t),
                lerp(left_color[2], right_color[2], t),
            )

    return PALETTE[-1][1]


def make_sunflower_positions(
    count: int, radius: float
) -> list[tuple[float, float, float]]:
    if count <= 0:
        return []

    golden_angle = math.pi * (1.0 - math.sqrt(5.0))
    positions: list[tuple[float, float, float]] = []
    max_index = max(count - 1, 1)

    for index in range(count):
        # Keep drone 0 exactly at the center, then place subsequent drones in
        # sunflower order so consecutive indices trace an outward spiral.
        r = radius * math.sqrt(index / max_index)
        theta = index * golden_angle
        positions.append((r * math.cos(theta), r * math.sin(theta), 0.0))

    return positions


def make_pixel_positions(
    positions: list[tuple[float, float, float]],
) -> list[tuple[float, float]]:
    max_extent = max(max(abs(x), abs(y)) for x, y, _ in positions) or 1.0
    drawable = IMAGE_SIZE - 2 * MARGIN
    scale = drawable / (2.0 * max_extent)
    center = IMAGE_SIZE / 2.0

    pixel_positions: list[tuple[float, float]] = []
    for x, y, _ in positions:
        pixel_positions.append((center + x * scale, center - y * scale))

    return pixel_positions


def draw_axis_marker(draw: ImageDraw.ImageDraw) -> None:
    origin_x = 34
    origin_y = IMAGE_SIZE - 34
    axis_length = 26
    arrow_size = 5

    x_tip = (origin_x + axis_length, origin_y)
    y_tip = (origin_x, origin_y - axis_length)

    draw.line(((origin_x, origin_y), x_tip), fill=AXIS_MARKER, width=2)
    draw.line(((origin_x, origin_y), y_tip), fill=AXIS_MARKER, width=2)

    draw.line(
        (x_tip, (x_tip[0] - arrow_size, x_tip[1] - arrow_size // 2)),
        fill=AXIS_MARKER,
        width=2,
    )
    draw.line(
        (x_tip, (x_tip[0] - arrow_size, x_tip[1] + arrow_size // 2)),
        fill=AXIS_MARKER,
        width=2,
    )
    draw.line(
        (y_tip, (y_tip[0] - arrow_size // 2, y_tip[1] + arrow_size)),
        fill=AXIS_MARKER,
        width=2,
    )
    draw.line(
        (y_tip, (y_tip[0] + arrow_size // 2, y_tip[1] + arrow_size)),
        fill=AXIS_MARKER,
        width=2,
    )

    draw.text((x_tip[0] + 6, x_tip[1] - 9), "X", fill=AXIS_MARKER)
    draw.text((y_tip[0] - 6, y_tip[1] - 18), "Y", fill=AXIS_MARKER)


def draw_progress_bar(draw: ImageDraw.ImageDraw, time_fraction: float) -> None:
    top = IMAGE_SIZE - PROGRESS_BAR_HEIGHT
    clamped_fraction = clamp01(time_fraction)
    filled_width = round(IMAGE_SIZE * clamped_fraction)

    draw.rectangle(
        (0, top, IMAGE_SIZE - 1, IMAGE_SIZE - 1),
        fill=PROGRESS_BAR_TRACK,
    )

    if filled_width <= 0:
        return

    draw.rectangle(
        (0, top, filled_width - 1, IMAGE_SIZE - 1),
        fill=PROGRESS_BAR,
    )


def draw_guides(draw: ImageDraw.ImageDraw) -> None:
    draw.ellipse(
        (MARGIN, MARGIN, IMAGE_SIZE - MARGIN, IMAGE_SIZE - MARGIN),
        outline=GUIDE,
        width=2,
    )
    center = IMAGE_SIZE / 2.0
    draw.line((center, MARGIN, center, IMAGE_SIZE - MARGIN), fill=GUIDE, width=1)
    draw.line((MARGIN, center, IMAGE_SIZE - MARGIN, center), fill=GUIDE, width=1)
    draw_axis_marker(draw)


def render_preset(
    meta,
    positions: list[tuple[float, float, float]],
    pixel_positions: list[tuple[float, float]],
    output_dir: Path,
    layout: str,
    draw_connector_line: bool,
) -> Path:
    frames: list[Image.Image] = []
    total_frames = FRAME_END - FRAME_START + 1

    for frame in range(FRAME_START, FRAME_END + 1):
        time_fraction = (
            0.0 if total_frames <= 1 else (frame - FRAME_START) / (total_frames - 1)
        )

        image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), BACKGROUND)
        draw = ImageDraw.Draw(image)
        draw_guides(draw)
        draw_progress_bar(draw, time_fraction)

        colors: list[tuple[int, int, int]] = []
        for drone_index, position in enumerate(positions):
            value = clamp01(
                meta.function(
                    frame=frame,
                    time_fraction=time_fraction,
                    drone_index=drone_index,
                    formation_index=drone_index,
                    position=position,
                    drone_count=len(positions),
                )
            )
            colors.append(color_for_value(value))

        if draw_connector_line:
            for index in range(len(pixel_positions) - 1):
                start = pixel_positions[index]
                end = pixel_positions[index + 1]
                draw.line((start, end), fill=CONNECTOR_LINE, width=1)

        for (px, py), color in zip(pixel_positions, colors):
            draw.ellipse(
                (px - DOT_RADIUS, py - DOT_RADIUS, px + DOT_RADIUS, py + DOT_RADIUS),
                fill=color,
            )

        frames.append(image.convert("P", palette=_ADAPTIVE_PALETTE))

    if layout == "subdirs":
        target_dir = output_dir / meta.id
        target_dir.mkdir(parents=True, exist_ok=True)
        output_path = target_dir / "preview.gif"
    else:
        output_path = output_dir / f"{meta.id}.gif"

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / FPS),
        loop=0,
        disposal=2,
    )

    return output_path


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    positions = make_sunflower_positions(args.drone_count, SUNFLOWER_RADIUS)
    pixel_positions = make_pixel_positions(positions)

    presets = list(iter_preset_mapping())

    print(
        f"Rendering {len(presets)} preset previews into {output_dir} "
        f"using {args.drone_count} drones"
    )
    print(
        "Note: all drones use z=0, so Z/XZ/YZ-based presets will look flatter by design."
    )

    failures: list[tuple[str, Exception]] = []

    for meta in presets:
        print(f"  -> {meta.id}")
        try:
            output_path = render_preset(
                meta=meta,
                positions=positions,
                pixel_positions=pixel_positions,
                output_dir=output_dir,
                layout=args.layout,
                draw_connector_line=args.draw_connector_line,
            )
            print(f"     saved {output_path}")
        except Exception as exc:
            failures.append((meta.id, exc))
            print(f"     FAILED: {exc}")

    if failures:
        print("\nSome presets failed:")
        for preset_id, exc in failures:
            print(f"  - {preset_id}: {exc}")
        return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
