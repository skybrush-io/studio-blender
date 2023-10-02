from bpy.types import Operator

from sbstudio.model.file_formats import update_supported_file_formats_from_limits
from sbstudio.plugin.api import call_api_from_blender_operator

__all__ = ("RefreshFileFormatsOperator",)


class RefreshFileFormatsOperator(Operator):
    """Queries the server for the list of file formats that are supported by
    the server.
    """

    bl_idname = "skybrush.refresh_file_formats"
    bl_label = "Query File Formats"
    bl_description = "Queries the supported file formats from the server"
    bl_options = {"REGISTER"}

    def execute(self, context):
        try:
            with call_api_from_blender_operator(
                self, "server capabilities query"
            ) as api:
                update_supported_file_formats_from_limits(api.get_limits())
        except Exception:
            return {"CANCELLED"}
        return {"FINISHED"}
