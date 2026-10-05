"""Compile linear RGB keyframes to the public Skybrush LED instruction format.

Protocol reference: skybrush-io/libskybrush src/lights/commands.cpp and
executor.cpp. Durations are unsigned LEB128 counts of 20 ms ticks.
"""

from base64 import b64encode
from math import isfinite


def _varuint(value: int) -> bytes:
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def compile_light_keyframes(keyframes) -> str:
    """Encode fades and steps, quantizing absolute times to avoid timing drift.

    Quantization error is at most 10 ms per keyframe. Empty programs retain
    the player's default color. Invalid input is rejected rather than clipped.
    """
    program = bytearray()
    previous_time = 0.0
    previous_tick = 0
    for index, (time, color, fade) in enumerate(keyframes):
        if not isfinite(time) or time < previous_time or time < 0:
            raise ValueError("light timestamps must be finite, nonnegative and ordered")
        if len(color) != 3 or any(
            not isinstance(c, int) or isinstance(c, bool) or not 0 <= c <= 255
            for c in color
        ):
            raise ValueError("light colors must contain three integer bytes")
        if fade not in (0, 1):
            raise ValueError("light fade flag must be 0 or 1")
        tick = round(time * 50)
        if tick > 0xFFFFFFFF // 20:
            raise ValueError("light timeline exceeds the 32-bit player clock")
        duration = tick - previous_tick
        if index > 0 and fade and duration:
            program.extend(bytes((8, *color)) + _varuint(duration))
        else:
            if duration:
                program.extend(b"\x02" + _varuint(duration))
            program.extend(bytes((4, *color, 0)))
        previous_time, previous_tick = time, tick
    program.append(0)
    return b64encode(program).decode("ascii")
