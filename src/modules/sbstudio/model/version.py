from sbstudio.api.types import Version
from sbstudio.plugin.constants import MINIMUM_BACKEND_VERSION

_version: Version


__all__ = (
    "get_backend_version",
    "is_backend_version_ok",
)


def is_backend_version_ok() -> bool:
    """Returns whether the stored backend version is above the
    current minimum requirement."""
    global _version

    return _version >= MINIMUM_BACKEND_VERSION


def get_backend_version() -> Version:
    """Returns the version of the server backend."""
    global _version

    return _version


def update_backend_version(version: Version) -> None:
    """Updates the backend version object returned from a server API call."""
    global _version

    _version = version


update_backend_version(MINIMUM_BACKEND_VERSION)
