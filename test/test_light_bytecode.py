import os
import subprocess
from base64 import b64decode

import pytest
from sbstudio.light_bytecode import compile_light_keyframes


def test_matches_licensed_red_to_blue_six_second_reference():
    assert (
        compile_light_keyframes([[0, [255, 0, 0], 0], [6, [0, 0, 255], 1]])
        == "BP8AAAAIAAD/rAIA"
    )


def test_steps_wait_before_changing_color():
    data = b64decode(
        compile_light_keyframes([[0, [255, 0, 0], 0], [1, [0, 0, 255], 0]])
    )
    assert data == bytes([4, 255, 0, 0, 0, 2, 50, 4, 0, 0, 255, 0, 0])


@pytest.mark.parametrize(
    "frames",
    [
        [[-1, [0, 0, 0], 0]],
        [[float("nan"), [0, 0, 0], 0]],
        [[0, [256, 0, 0], 0]],
        [[0, [1.5, 0, 0], 0]],
        [[1, [0, 0, 0], 0], [0, [0, 0, 0], 0]],
    ],
)
def test_rejects_invalid_input(frames):
    with pytest.raises(ValueError):
        compile_light_keyframes(frames)


def test_native_decoder_playback(tmp_path):
    reader = os.environ.get("DRONETARA_LIGHT_READER")
    if not reader:
        pytest.skip("set DRONETARA_LIGHT_READER to the compiled libskybrush adapter")
    path = tmp_path / "lights.bin"
    path.write_bytes(
        b64decode(
            compile_light_keyframes(
                [
                    [0, [255, 0, 0], 0],
                    [6, [0, 0, 255], 1],
                    [8, [0, 255, 0], 0],
                ]
            )
        )
    )
    output = subprocess.check_output(
        [reader, str(path), "0", "3000", "6000", "7000", "8000", "9000", "3000"],
        text=True,
    )
    rows = [list(map(int, line.split())) for line in output.splitlines()]
    assert rows[0][1:] == [255, 0, 0]
    assert all(abs(a - b) <= 1 for a, b in zip(rows[1][1:], [127, 0, 127]))
    assert rows[2][1:] == rows[3][1:] == [0, 0, 255]
    assert rows[4][1:] == rows[5][1:] == [0, 255, 0]
    assert rows[6] == rows[1]  # Random access rewinds correctly.
