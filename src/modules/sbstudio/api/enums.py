from enum import Enum

__all__ = ("SkybrushJSONFormat",)


class SkybrushJSONFormat(Enum):
    """Enum class defining the different JSON formats of Skybrush."""

    # the standard raw Skybrush JSON format used by skybrush converter
    RAW = 0

    # the online Skybrush JSON format to be sent as a http request
    ONLINE = 1
