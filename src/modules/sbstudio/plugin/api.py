from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from socket import gaierror
from typing import TYPE_CHECKING, TypedDict, TypeVar
from urllib.error import URLError

from sbstudio.api import SkybrushStudioAPI
from sbstudio.api.version import ensure_backend_version
from sbstudio.errors import SkybrushStudioError

from .errors import SkybrushStudioExportWarning, TaskCancelled
from .plugin_helpers import only_with_online_access

if TYPE_CHECKING:
    from bpy.types import Operator


__all__ = ("get_api", "call_api_from_blender_operator")

T = TypeVar("T")

#############################################################################
# configure logger

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_api_from_url_and_key(url: str, key: str) -> SkybrushStudioAPI:
    """Constructs a Skybrush Studio API object from a root URL and an API key.

    Memoized so we do not need to re-construct the same instance as long as
    the user does not change the add-on settings.
    """
    try:
        result = SkybrushStudioAPI(api_key=key or None)
        if url:
            result.url = url
    except ValueError as ex:
        log.error(f"Could not initialize Skybrush Studio API: {str(ex)}")
        raise
    except Exception as ex:
        log.error(f"Unhandled exception in Skybrush Studio API initialization: {ex!r}")
        raise

    # This is bad practice, but the default installation of Blender does not find
    # the SSL certificates on macOS and there are reports about similar problems
    # on Windows as well
    # TODO(ntamas): sort this out!
    result._skip_ssl_checks()

    return result


class APISettings(TypedDict):
    """Dictionary representing the settings required to construct a SkybrushStudioAPI_
    object instance.
    """

    server_url: str
    """URL of the server to connect to"""

    api_key: str
    """API key to include in headers when sending requests to the server"""


def get_api_settings() -> APISettings:
    """Returns the API-related settings from the global add-on preferences."""
    from sbstudio.plugin.model.global_settings import get_preferences

    prefs = get_preferences()

    return {
        "api_key": str(prefs.api_key).strip(),
        "server_url": str(prefs.server_url).strip(),
    }


@only_with_online_access
def get_api(*, check_version: bool = True) -> SkybrushStudioAPI:
    """Returns the singleton instance of the Skybrush Studio API object.

    Optionally also checks the version number of the backend if it is not known
    yet.

    Args:
        check_version: whether to check the version of the backend
    """
    settings = get_api_settings()
    api = _get_api_from_url_and_key(**settings)
    if check_version:
        ensure_backend_version(api)

    return api


@contextmanager
def call_api_from_blender_operator(
    operator: Operator, what: str = "operation", *, check_version: bool = True
) -> Iterator[SkybrushStudioAPI]:
    """Context manager that yields immediately back to the caller from a
    try-except block, catches all exceptions, and calls the ``report()`` method
    of the given Blender operator with an appropriate error message if there
    was an error. All exceptions are then re-raised; the caller is expected to
    return ``{"CANCELLED"}`` from the operator immediately in response to an
    exception.

    Args:
        check_version: whether to check the version number of the backend
    """
    default_message = f"Error while invoking {what} on the Skybrush Studio server"
    try:
        # TODO(ntamas): This is not entirely correct here. When an exception happens
        # during get_api(...), we will not yield anything back to the caller. If we
        # handle _that_ exception without re-raising it, the caller itself will raise
        # a "generator didn't yield" exception, which is quite confusing.
        yield get_api(check_version=check_version)
    except SkybrushStudioExportWarning as ex:
        operator.report({"WARNING"}, str(ex))
        raise
    except SkybrushStudioError as ex:
        operator.report({"ERROR"}, ex.format_message() or default_message)
        raise
    except URLError as ex:
        if isinstance(ex.reason, ConnectionRefusedError):
            message = f"{default_message}: Connection refused. Is the server running?"
        elif isinstance(ex.reason, gaierror):
            message = f"{default_message}: Could not resolve server URL. Are you connected to the Internet?"
        elif isinstance(ex.reason, OSError):
            message = f"{default_message}: {ex.reason.strerror}"
        elif isinstance(ex.reason, str):
            message = f"{default_message}: {ex.reason}"
        else:
            message = default_message
        operator.report({"ERROR"}, message)
        raise
    except ConnectionRefusedError:
        operator.report(
            {"ERROR"}, f"{default_message}: Connection refused. Is the server running?"
        )
        raise
    except gaierror:
        # gaierror is short for "getaddrinfo" error, which happens when trying
        # to look up the hostname in the server URL while not being connected
        # to the Internet (or without a DNS server)
        operator.report(
            {"ERROR"},
            f"{default_message}: Could not resolve server URL. Are you connected to the Internet?",
        )
        raise
    except OSError as ex:
        operator.report({"ERROR"}, f"{default_message}: {ex.strerror}")
        raise
    except (TaskCancelled, KeyboardInterrupt):
        operator.report({"ERROR"}, "Operation cancelled by user.")
        raise
    except Exception as ex:
        operator.report({"ERROR"}, f"{default_message}: Unexpected error ({ex})")
        raise
