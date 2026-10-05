"""Blender-independent conversion using Blender's effective frame rate."""

from math import isfinite


def effective_fps(render) -> float:
    fps, base = float(render.fps), float(render.fps_base)
    if not all(isfinite(value) and value > 0 for value in (fps, base)):
        raise ValueError("frame rate and frame-rate base must be finite and positive")
    return fps / base


def export_segments(segments, start: float, end: float):
    """Clip authored intervals to the export range and shift its origin.

    Reversed intervals are retained as invalid metadata for the validator.
    Empty intervals remain explicit, rather than inventing a phase duration.
    """
    result = {}
    for name, (left, right) in segments.items():
        if right < left:
            result[name] = (left - start, right - start)
        elif right >= start and left <= end:
            result[name] = (max(left, start) - start, min(right, end) - start)
    return result
