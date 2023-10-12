import bpy

from bpy.props import StringProperty
from bpy.types import Operator

__all__ = ("SetServerURLOperator",)


class SetServerURLOperator(Operator):
    """Sets the server URL to a fixed value."""

    bl_idname = "skybrush.set_server_url"
    bl_label = "Set server URL"
    bl_description = "Sets the server URL to a fixed value"

    url = StringProperty(default="")

    def execute(self, context):
        from sbstudio.plugin.model.global_settings import get_preferences

        prefs = get_preferences()
        prefs.server_url = self.url

        bpy.ops.wm.save_userpref()

        try:
            bpy.ops.skybrush.refresh_file_formats()
        except RuntimeError:
            # Maybe the server is not running?
            pass

        return {"FINISHED"}
