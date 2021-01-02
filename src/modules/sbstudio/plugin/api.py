import bpy

from sbstudio.plugin.model.global_settings import DroneShowAddonGlobalSettings

__all__ = ("get_api",)

#: One singleton API object that the entire Blender plugin uses to talk to
#: Skybrush Studio. Constructed lazily so we can defer importing the API.
_api = None

#: Set this boolean to `True` if you are using the API with a local server
_local = True


def get_api():
    """Returns the singleton instance of the Skybrush Studio API object."""
    global _api, _local

    if _api is None:
        from sbstudio.api import SkybrushStudioAPI

        _api = SkybrushStudioAPI()

        # This is bad practice, but the default installation of Blender does not find
        # the SSL certificates on macOS and there are reports about similar problems
        # on Windows as well
        # TODO(ntamas): sort this out!
        _api._skip_ssl_checks()

    prefs = bpy.context.preferences
    try:
        prefs = prefs.addons[DroneShowAddonGlobalSettings.bl_idname].preferences
        api_key = prefs.api_key
    except KeyError:
        api_key = None

    _api.api_key = api_key

    if _local:
        _api.url = "http://localhost:8000"

    return _api
