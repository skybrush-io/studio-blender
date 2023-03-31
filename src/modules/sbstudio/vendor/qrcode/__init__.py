# qrcode v5.3.1, Copyright (c) 2011- Lincoln Loop.
#
# This is a vendored copy of the qrcode Python library, version 5.3.1, slightly
# adapted for the Blender environment. Unneeded parts related to image generation
# were stripped. Code was reformatted with black; absolute imports were changed
# to relative where possible.
#
# All files in this folder are licensed under the MIT License, according to
# the original licensing terms of qrcode 5.3.1.
#
# Refer to the original source code for more information:
#
# https://github.com/lincolnloop/python-qrcode

from .constants import (
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
    ERROR_CORRECT_H,
)
from .main import make, QRCode

__all__ = (
    "make",
    "QRCode",
    "ERROR_CORRECT_L",
    "ERROR_CORRECT_M",
    "ERROR_CORRECT_Q",
    "ERROR_CORRECT_H",
)
