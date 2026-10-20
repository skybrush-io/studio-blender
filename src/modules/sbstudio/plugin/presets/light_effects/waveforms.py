"""Waveform shapes that turn a per-drone phase into a per-drone brightness.

The presets in this package all work the same way: compute a phase that advances with
time (and sometimes with position or formation index), then shape it with a waveform.
This module holds these commonly used waveform shapes.
"""

from __future__ import annotations

from numpy import abs, clip, cos, float32, floating, pi, sin
from numpy.typing import NDArray

__all__ = ("cosine_wave", "sine_wave", "steepen", "triangle_wave")


def triangle_wave(phase: NDArray[floating]) -> NDArray[float32]:
    """Returns a triangle wave for the given per-drone phase.

    Args:
        phase: per-drone input phase, in cycles (one full period is 1.0);
            the phase is wrapped into [0, 1), so e.g. 1.25 behaves like 0.25

    Returns:
        per-drone brightness according to a triangle wave, in [0, 1].
    """
    v = phase % 1.0
    return (1 - abs(2 * v - 1)).astype(float32)


def sine_wave(phase: NDArray[floating]) -> NDArray[float32]:
    """Returns a sine wave for the given per-drone phase.

    Args:
        phase: per-drone input phase, in cycles (one full period is 1.0)

    Returns:
        per-drone brightness according to a sine wave, in [0, 1].
    """
    return ((sin(2 * pi * (phase % 1.0)) + 1) / 2).astype(float32)


def cosine_wave(phase: NDArray[floating]) -> NDArray[float32]:
    """Returns a cosine wave for the given per-drone phase.

    Args:
        phase: per-drone input phase, in cycles (one full period is 1.0)

    Returns:
        per-drone brightness according to a cosine wave, in [0, 1].
    """
    return ((cos(2 * pi * (phase % 1.0)) + 1) / 2).astype(float32)


def steepen(brightness: NDArray[floating]) -> NDArray[float32]:
    """Steepens a brightness ramp into a pulse with flat dark and bright edges.

    The [0.25; 0.75] part of the input range is mapped linearly onto [0; 1], so the
    ramp becomes twice as steep, and everything outside that range is clipped.

    Args:
        brightness: per-drone brightness, in [0, 1]

    Returns:
        per-drone brightness of the steepened pulse, in [0, 1].
    """
    return clip(2 * (brightness - 0.25), 0, 1).astype(float32)
