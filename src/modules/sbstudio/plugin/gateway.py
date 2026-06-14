from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from socket import gaierror
from typing import TYPE_CHECKING, TypedDict, TypeVar
from urllib.error import URLError

from sbstudio.api import SkybrushGatewayAPI
from sbstudio.api.errors import SkybrushStudioAPIError
from sbstudio.errors import SkybrushStudioError

from .errors import TaskCancelled
from .plugin_helpers import only_with_online_access

if TYPE_CHECKING:
    from bpy.types import Operator

__all__ = (
    "get_gateway",
    "get_gateway_if_configured",
    "call_gateway_from_blender_operator",
)

T = TypeVar("T")

#############################################################################
# configure logger

log = logging.getLogger(__name__)


class GatewaySettings(TypedDict):
    """Dictionary representing the settings required to construct a SkybrushGatewayAPI_
    object instance.
    """

    url: str
    """URL of the gateway to connect to"""


def _get_gateway_settings() -> GatewaySettings:
    """Returns the gateway-related settings from the global add-on preferences."""
    from sbstudio.plugin.model.global_settings import get_preferences

    prefs = get_preferences()
    mode = prefs.operation_mode

    match mode:
        case "CLOUD":
            # Cloud setting uses a fixed URL from localhost
            url = "http://localhost:7999"

        case "ADVANCED":
            # Advanced mode uses whatever the user entered
            url = str(prefs.gateway_url).strip()

        case _:
            # All other modes do not need a gateway
            url = ""

    return {"url": url}


@lru_cache(maxsize=1)
def _get_gateway_from_url(url: str) -> SkybrushGatewayAPI | None:
    """Constructs a Skybrush Gateway API object from a root URL.

    Memoized so we do not need to re-construct the same instance as long as
    the user does not change the add-on settings.

    Args:
        url: the root URL of the gateway API or an empty string if no gateway needs to
            be used

    Raises:
        ValueError: on initialization error
    """
    if not url:
        return None

    try:
        result = SkybrushGatewayAPI(url=url)
    except ValueError as ex:
        log.error(f"Could not initialize Skybrush Gateway API: {str(ex)}")
        raise
    except Exception as ex:
        log.error(f"Unhandled exception in Skybrush Gateway API initialization: {ex!r}")
        raise

    # This is bad practice, but the default installation of Blender does not find
    # the SSL certificates on macOS and there are reports about similar problems
    # on Windows as well
    # TODO(ntamas): sort this out!
    result._skip_ssl_checks()

    return result


def get_gateway() -> SkybrushGatewayAPI:
    """Returns the singleton instance of the Skybrush Gateway API object.

    Raises:
        SkybrushStudioAPIError: if gateway is not configured
    """
    gateway = get_gateway_if_configured()
    if gateway is None:
        raise SkybrushStudioAPIError(
            "Skybrush Gateway is not configured in the preferences"
        )

    return gateway


@only_with_online_access
def get_gateway_if_configured() -> SkybrushGatewayAPI | None:
    """Returns the singleton instance of the Skybrush Gateway API object if it is
    configured, ``None`` otherwise.
    """
    settings = _get_gateway_settings()
    return _get_gateway_from_url(**settings)


@contextmanager
def call_gateway_from_blender_operator(
    operator: Operator, what: str = "operation"
) -> Iterator[SkybrushGatewayAPI]:
    """Context manager that yields immediately back to the caller from a
    try-except block, catches all exceptions, and calls the ``report()`` method
    of the given Blender operator with an appropriate error message if there
    was an error. All exceptions are then re-raised; the caller is expected to
    return ``{"CANCELLED"}`` from the operator immediately in response to an
    exception.
    """
    default_message = f"Error while invoking {what} on the Skybrush Studio gateway"
    try:
        # TODO(ntamas): This is not entirely correct here. When an exception happens
        # during get_api(...), we will not yield anything back to the caller. If we
        # handle _that_ exception without re-raising it, the caller itself will raise
        # a "generator didn't yield" exception, which is quite confusing.
        yield get_gateway()
    except SkybrushStudioError as ex:
        operator.report({"ERROR"}, ex.format_message() or default_message)
        raise
    except URLError as ex:
        if isinstance(ex.reason, ConnectionRefusedError):
            message = f"{default_message}: Connection refused. Is the gateway running?"
        elif isinstance(ex.reason, gaierror):
            message = f"{default_message}: Could not resolve gateway URL. Are you connected to the Internet?"
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
            {"ERROR"}, f"{default_message}: Connection refused. Is the gateway running?"
        )
        raise
    except gaierror:
        # gaierror is short for "getaddrinfo" error, which happens when trying
        # to look up the hostname in the server URL while not being connected
        # to the Internet (or without a DNS server)
        operator.report(
            {"ERROR"},
            f"{default_message}: Could not resolve gateway URL. Are you connected to the Internet?",
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
