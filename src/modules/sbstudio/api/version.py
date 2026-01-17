from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import MINIMUM_BACKEND_VERSION
from .errors import BackendVersionMismatchError
from .types import Version

if TYPE_CHECKING:
    from sbstudio.plugin.api import SkybrushStudioAPI

__all__ = ("ensure_backend_version",)

_backend_version_cache: tuple[SkybrushStudioAPI, Version] | None = None


def _get_or_query_backend_version(
    api: SkybrushStudioAPI, *, force: bool = False
) -> Version:
    """Returns the version of the server backend, querying it from the server
    using the given API object if needed.

    Args:
        api: the API object to use for the query
        force: whether to force the query even if we know the backend version
    """
    global _backend_version_cache

    if not force and _backend_version_cache is not None:
        cached_api, cached_version = _backend_version_cache
        if cached_api == api:
            return cached_version

    version = api.get_version()
    _backend_version_cache = (api, version)

    return version


def ensure_backend_version(api: SkybrushStudioAPI):
    """Ensures that the version number of the backend is larger than or equal
    to the minimum required version number.

    This function re-uses the cached version number if we already know the
    version number of the backend.

    Args:
        api: the API object to use for the query

    Raises:
        BackendVersionMismatchError: if the backend version is not suitable
    """
    global _backend_version

    version = _get_or_query_backend_version(api)
    if version < MINIMUM_BACKEND_VERSION:
        raise BackendVersionMismatchError(version)
