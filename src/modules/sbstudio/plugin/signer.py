import logging

from contextlib import contextmanager
from functools import lru_cache
from socket import gaierror
from typing import Iterator, TypeVar
from urllib.error import URLError

from sbstudio.api import SkybrushSignerAPI
from sbstudio.api.errors import NoOnlineAccessAllowedError, SkybrushStudioAPIError
from sbstudio.plugin.errors import SkybrushStudioExportWarning

__all__ = ("get_signer",)

T = TypeVar("T")

#############################################################################
# configure logger

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_signer_from_url(url: str):
    """Constructs a Skybrush Signer API object from a root URL.

    Memoized so we do not need to re-construct the same instance as long as
    the user does not change the add-on settings.
    """
    try:
        result = SkybrushSignerAPI(url=url)
    except ValueError as ex:
        log.error(f"Could not initialize Skybrush Signer API: {str(ex)}")
        raise
    except Exception as ex:
        log.error(f"Unhandled exception in Skybrush Signer API initialization: {ex!r}")
        raise

    # This is bad practice, but the default installation of Blender does not find
    # the SSL certificates on macOS and there are reports about similar problems
    # on Windows as well
    # TODO(ntamas): sort this out!
    result._skip_ssl_checks()

    return result


def get_signer() -> SkybrushSignerAPI:
    """Returns the singleton instance of the Skybrush Signer API object."""
    from sbstudio.plugin.plugin_helpers import is_online_access_allowed
    from sbstudio.plugin.model.global_settings import get_preferences

    if not is_online_access_allowed():
        raise NoOnlineAccessAllowedError()

    signer_url: str

    prefs = get_preferences()
    signer_url = str(prefs.signer_url).strip()

    signer = _get_signer_from_url(signer_url)

    return signer


# TODO(vasarhelyi): this is so far a copy of call_api_from_blender_operator(),
# might not be needed at all
@contextmanager
def call_signer_from_blender_operator(
    operator, what: str = "operation"
) -> Iterator[SkybrushSignerAPI]:
    """Context manager that yields immediately back to the caller from a
    try-except block, catches all exceptions, and calls the ``report()`` method
    of the given Blender operator with an appropriate error message if there
    was an error. All exceptions are then re-raised; the caller is expected to
    return ``{"CANCELLED"}`` from the operator immediately in response to an
    exception.
    """
    default_message = f"Error while invoking {what} on the Skybrush Signer"
    try:
        yield get_signer()
    except SkybrushStudioExportWarning as ex:
        operator.report({"WARNING"}, str(ex))
        raise
    except SkybrushStudioAPIError as ex:
        operator.report({"ERROR"}, ex.format_message() or default_message)
        raise
    except URLError as ex:
        if isinstance(ex.reason, ConnectionRefusedError):
            message = f"{default_message}: Connection refused. Is the signer running?"
        elif isinstance(ex.reason, gaierror):
            message = f"{default_message}: Could not resolve signer URL. Are you connected to the Internet?"
        elif isinstance(ex.reason, OSError):
            message = f"{default_message}: {ex.reason.strerror}"
        elif isinstance(ex.reason, str):
            message = f"{default_message}: {ex.reason}"
        else:
            message = default_message
        operator.report({"ERROR"}, message)
    except ConnectionRefusedError:
        operator.report(
            {"ERROR"}, f"{default_message}: Connection refused. Is the signer running?"
        )
        raise
    except gaierror:
        # gaierror is short for "getaddrinfo" error, which happens when trying
        # to look up the hostname in the signer URL while not being connected
        # to the Internet (or without a DNS server)
        operator.report(
            f"{default_message}: Could not resolve signer URL. Are you connected to the Internet?"
        )
    except OSError as ex:
        operator.report({"ERROR"}, f"{default_message}: {ex.strerror}")
        raise
    except Exception:
        operator.report({"ERROR"}, default_message)
        raise
