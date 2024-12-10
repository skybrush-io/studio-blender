import logging

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator, Optional, TypeVar

from sbstudio.api import SkybrushStudioAPI
from sbstudio.api.errors import NoOnlineAccessAllowedError, SkybrushStudioAPIError
from sbstudio.plugin.errors import SkybrushStudioExportWarning

__all__ = ("get_api",)

_fallback_api_key: str = "trial"
"""Fallback API key to use when the user did not enter any API key"""

T = TypeVar("T")

#############################################################################
# configure logger

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_api_from_url_and_key_or_license(url: str, key: str, license_file: str):
    """Constructs a Skybrush Studio API object from a root URL and an API key
    or a license file.

    Memoized so we do not need to re-construct the same instance as long as
    the user does not change the add-on settings.
    """
    global _fallback_api_key

    try:
        result = SkybrushStudioAPI(
            api_key=key or (None if license_file else _fallback_api_key),
            license_file=license_file or None,
        )
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


def get_api() -> SkybrushStudioAPI:
    """Returns the singleton instance of the Skybrush Studio API object."""
    from sbstudio.plugin.plugin_helpers import is_online_access_allowed
    from sbstudio.plugin.model.global_settings import get_preferences

    if not is_online_access_allowed():
        raise NoOnlineAccessAllowedError()

    api_key: str
    server_url: str
    license_file: str

    prefs = get_preferences()
    api_key = str(prefs.api_key).strip()
    license_file = str(prefs.license_file).strip()
    server_url = str(prefs.server_url).strip()

    return _get_api_from_url_and_key_or_license(server_url, api_key, license_file)


@contextmanager
def call_api_from_blender_operator(
    operator, what: str = "operation"
) -> Iterator[SkybrushStudioAPI]:
    """Context manager that yields immediately back to the caller from a
    try-except block, catches all exceptions, and calls the ``report()`` method
    of the given Blender operator with an appropriate error message if there
    was an error. All exceptions are then re-raised; the caller is expected to
    return ``{"CANCELLED"}`` from the operator immediately in response to an
    exception.
    """
    default_message = f"Error while invoking {what} on the Skybrush Studio server"
    try:
        yield get_api()
    except NoOnlineAccessAllowedError:
        operator.report(
            {"ERROR"},
            "Access of online resources is disabled in the Blender "
            + "preferences. Please enable online access and then try again.",
        )
        raise
    except SkybrushStudioExportWarning as ex:
        operator.report({"WARNING"}, str(ex))
        raise
    except SkybrushStudioAPIError as ex:
        operator.report({"ERROR"}, str(ex) or default_message)
        raise
    except Exception:
        operator.report({"ERROR"}, default_message)
        raise


def set_fallback_api_key(value: Optional[str]) -> None:
    """Sets the fallback API key to use when the user did not provide one in the
    add-on preferences.
    """
    global _fallback_api_key
    _fallback_api_key = str(value) if value is not None else ""
