import logging

from functools import lru_cache
from typing import TypeVar

from sbstudio.api import SkybrushSignerAPI
from sbstudio.api.errors import NoOnlineAccessAllowedError, SkybrushStudioAPIError

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

    Raises:
        ValueError on initialization error
        Exception on all other unhandled exceptions
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
    """Returns the singleton instance of the Skybrush Signer API object.

    Raises:
        SkybrushStudioAPIError if signer is not configured
    """
    from sbstudio.plugin.plugin_helpers import is_online_access_allowed
    from sbstudio.plugin.model.global_settings import get_preferences

    if not is_online_access_allowed():
        raise NoOnlineAccessAllowedError()

    signer_url: str

    prefs = get_preferences()
    signer_url = str(prefs.signer_url).strip()

    if not signer_url:
        raise SkybrushStudioAPIError(
            "Request signer is not configured in the preferences"
        )

    signer = _get_signer_from_url(signer_url)

    return signer
