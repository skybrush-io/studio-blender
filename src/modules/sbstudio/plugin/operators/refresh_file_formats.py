from bpy.types import Operator

from sbstudio.model.file_formats import update_supported_file_formats_from_limits
from sbstudio.model.version import (
    get_backend_version,
    is_backend_version_ok,
    update_backend_version,
)
from sbstudio.plugin.api import call_api_from_blender_operator
from sbstudio.plugin.constants import MINIMUM_BACKEND_VERSION

__all__ = ("RefreshFileFormatsOperator",)


class RefreshFileFormatsOperator(Operator):
    """Queries the server for the list of file formats that are supported by
    the server.

    Note that operator also checks the backend version in the background and
    informs the user if the backend is outdated.
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
                update_backend_version(api.get_version())
        except Exception:
            return {"CANCELLED"}

        if not is_backend_version_ok():
            self.report(
                {"WARNING"},
                f"Skybrush Studio Server is outdated ({get_backend_version()}), "
                f"update to {MINIMUM_BACKEND_VERSION} or above!",
            )

        return {"FINISHED"}
