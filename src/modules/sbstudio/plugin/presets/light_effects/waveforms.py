"""Waveform shapes that turn a per-drone phase into a per-drone brightness.

The presets in this package all work the same way: compute a phase that advances with
time (and sometimes with position or formation index), then shape it with a waveform.
This module holds the shapes, so that "triangle wave" is written once rather than at
every call site.

A phase may have any floating point precision. The arithmetic runs in the precision of
the input and the result is narrowed to float32 on return, which matters for callers
whose phase is float64 and needs the extra intermediate precision.
"""

from __future__ import annotations

from numpy import abs, float32, floating
from numpy.typing import NDArray

__all__ = ("triangle_wave",)


def triangle_wave(phase: NDArray[floating]) -> NDArray[float32]:
    """Returns a triangle wave for the given per-drone phase.

    The phase is wrapped into ``[0; 1)`` first, so a phase of 1.25 gives the same
    brightness as 0.25. Brightness is 1.0 where the wrapped phase is 0.5, falling to
    0.0 where it is 0 or 1, and rising again in between.
    """
    v = phase % 1.0
    return (1 - abs(2 * v - 1)).astype(float32)
