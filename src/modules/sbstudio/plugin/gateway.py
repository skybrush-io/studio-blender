import logging

from functools import lru_cache
from typing import TypeVar

from sbstudio.api import SkybrushGatewayAPI
from sbstudio.api.errors import NoOnlineAccessAllowedError, SkybrushStudioAPIError

__all__ = ("get_gateway",)

T = TypeVar("T")

#############################################################################
# configure logger

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_gateway_from_url(url: str) -> SkybrushGatewayAPI:
    """Constructs a Skybrush Gateway API object from a root URL.

    Memoized so we do not need to re-construct the same instance as long as
    the user does not change the add-on settings.

    Raises:
        ValueError: on initialization error
        Exception: on all other unhandled exceptions
    """
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
    from sbstudio.plugin.plugin_helpers import is_online_access_allowed
    from sbstudio.plugin.model.global_settings import get_preferences

    if not is_online_access_allowed():
        raise NoOnlineAccessAllowedError()

    prefs = get_preferences()
    gateway_url = str(prefs.gateway_url).strip()

    if not gateway_url:
        raise SkybrushStudioAPIError(
            "Skybrush Gateway is not configured in the preferences"
        )

    gateway = _get_gateway_from_url(gateway_url)

    return gateway
