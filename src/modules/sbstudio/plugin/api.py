import bpy

from contextlib import contextmanager
from typing import Iterator, Optional, TypeVar

from sbstudio.api import SkybrushStudioAPI
from sbstudio.api.errors import SkybrushStudioAPIError
from sbstudio.plugin.errors import SkybrushStudioExportWarning

__all__ = ("get_api",)

"""One singleton API object that the entire Blender plugin uses to talk to
Skybrush Studio. Constructed lazily so we can defer importing the API.
"""
_api: Optional[SkybrushStudioAPI] = None

_fallback_api_key: str = "trial"
"""Fallback API key to use when the user did not enter any API key"""

T = TypeVar("T")


def get_api() -> SkybrushStudioAPI:
    """Returns the singleton instance of the Skybrush Studio API object."""
    from sbstudio.plugin.model.global_settings import DroneShowAddonGlobalSettings

    global _api, _fallback_api_key

    if _api is None:
        _api = SkybrushStudioAPI()

        # This is bad practice, but the default installation of Blender does not find
        # the SSL certificates on macOS and there are reports about similar problems
        # on Windows as well
        # TODO(ntamas): sort this out!
        _api._skip_ssl_checks()

    api_key: str
    server_url: str

    prefs = bpy.context.preferences
    try:
        prefs = prefs.addons[DroneShowAddonGlobalSettings.bl_idname].preferences
        api_key = str(getattr(prefs, "api_key", "")).strip()
        server_url = str(getattr(prefs, "server_url", "")).strip()
    except KeyError:
        api_key = ""
        server_url = ""

    _api.api_key = api_key or _fallback_api_key
    if server_url:
        _api.url = server_url

    return _api


@contextmanager
def call_api_from_blender_operator(
    operator, what: str = "operation"
) -> Iterator[SkybrushStudioAPI]:
    """Context manager that yields immediately back to the caller from a
    try-except block, catches all exceptions, and calls the ``report()`` method
    of the given Blender operator with an approriate error message if there
    was an error. All exceptions are then re-raised; the caller is expected to
    return ``{"CANCELLED"}`` from the operator immediately in response to an
    exception.
    """
    default_message = (
        f"Error while invoking {what} on the Skybrush Studio online service"
    )
    try:
        yield get_api()
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
