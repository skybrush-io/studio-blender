"""Waveform shapes that turn a per-drone phase into a per-drone brightness.

The presets in this package all work the same way: compute a phase that advances with
time (and sometimes with position or formation index), then shape it with a waveform.
This module holds these commonly used waveform shapes.
"""

from __future__ import annotations

from numpy import abs, cos, float32, floating, sin
from numpy.typing import NDArray

__all__ = ("cosine_wave", "sine_wave", "triangle_wave")


def triangle_wave(phase: NDArray[floating]) -> NDArray[float32]:
    """Returns a triangle wave for the given per-drone phase.

    Args:
        phase: per-drone input phase, in radians

    Returns:
        per-drone brightness according to a triangle wave, in [0, 1].
    """
    v = phase % 1.0
    return (1 - abs(2 * v - 1)).astype(float32)


def sine_wave(phase: NDArray[floating]) -> NDArray[float32]:
    """Returns a sine wave for the given per-drone phase.

    Args:
        phase: per-drone input phase, in radians

    Returns:
        per-drone brightness according to a sine wave, in [0, 1].
    """
    return ((sin(phase) + 1) / 2).astype(float32)


def cosine_wave(phase: NDArray[floating]) -> NDArray[float32]:
    """Returns a cosine wave for the given per-drone phase.

    Args:
        phase: per-drone input phase, in radians

    Returns:
        per-drone brightness according to a cosine wave, in [0, 1].
    """
    return ((cos(phase) + 1) / 2).astype(float32)
