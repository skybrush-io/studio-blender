from enum import Enum
from typing import List, Tuple

from sbstudio.api.types import Limits

__all__ = (
    "FileFormat",
    "get_supported_file_formats",
)


class FileFormat(Enum):
    """List of file formats that we can potentially in export panels."""

    SKYC = "skyc"
    CSV = "csv"
    PDF = "pdf"
    DSS = "dss"
    DSS3 = "dss3"
    DAC = "dac"
    DROTEK = "drotek"
    EVSKY = "evsky"
    LITEBEE = "litebee"


_file_formats: Tuple[FileFormat, ...] = ()


def get_supported_file_formats() -> Tuple[FileFormat, ...]:
    """Returns the list of file formats that the server supports."""
    return _file_formats


def update_supported_file_formats_from_limits(limits: Limits) -> None:
    """Updates the list of file formats from a limits object returned from a
    server API call.
    """
    global _file_formats

    # .skyc and CSV are always supported
    formats: List[FileFormat] = [FileFormat.SKYC, FileFormat.CSV]

    # Add formats from the server (if any)
    for feature in limits.features:
        if feature == "export:dac":
            formats.append(FileFormat.DAC)
        elif feature == "export:dss":
            formats.append(FileFormat.DSS)
            formats.append(FileFormat.DSS3)
        elif feature == "export:drotek":
            formats.append(FileFormat.DROTEK)
        elif feature == "export:evsky":
            formats.append(FileFormat.EVSKY)
        elif feature == "export:litebee":
            formats.append(FileFormat.LITEBEE)
        elif feature == "export:plot":
            formats.append(FileFormat.PDF)

    _file_formats = tuple(formats)


update_supported_file_formats_from_limits(Limits.default())
