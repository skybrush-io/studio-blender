import bpy

from typing import Optional

from sbstudio.api import SkybrushStudioAPI
from sbstudio.plugin.model.global_settings import DroneShowAddonGlobalSettings

__all__ = ("get_api",)

#: One singleton API object that the entire Blender plugin uses to talk to
#: Skybrush Studio. Constructed lazily so we can defer importing the API.
_api = None

#: Fallback API key to use when the user did not enter any API key
_fallback_api_key: str = "trial"


def get_api():
    """Returns the singleton instance of the Skybrush Studio API object."""
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


def set_fallback_api_key(value: Optional[str]) -> None:
    """Sets the fallback API key to use when the user did not provide one in the
    add-on preferences.
    """
    global _fallback_api_key
    _fallback_api_key = str(value) if value is not None else ""
