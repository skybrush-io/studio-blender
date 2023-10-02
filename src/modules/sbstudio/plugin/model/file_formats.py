from enum import Enum
from typing import Tuple

__all__ = (
    "FileFormat",
    "get_supported_file_formats",
)


class FileFormat(Enum):
    """List of file formats that we can potentially in export panels."""

    SKYC = "skyc"
    CSV = "csv"
    PDF = "pdf"
    DDC = "ddc"
    DAC = "dac"
    DROTEK = "drotek"


_file_formats: Tuple[FileFormat, ...] = (
    FileFormat.SKYC,
    FileFormat.CSV,
    # FileFormat.PDF,
)


def get_supported_file_formats() -> Tuple[FileFormat, ...]:
    """Returns the list of file formats that the server supports."""
    return _file_formats
