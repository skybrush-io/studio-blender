from bpy.props import StringProperty
from bpy.types import AddonPreferences

from sbstudio.plugin.operators.set_server_url import SetServerURLOperator

__all__ = ("DroneShowAddonGlobalSettings",)


class DroneShowAddonGlobalSettings(AddonPreferences):
    """Global settings of the Skybrush Studio addon.

    This is active only when the addon is installed in the Blender add-on manager,
    not when it is provided to Blender dynamically at startup.
    """

    bl_idname = "ui_skybrush_studio"

    api_key = StringProperty(
        name="API Key",
        description="API Key that is used when communicating with the Skybrush Studio server",
    )

    server_url = StringProperty(
        name="Server URL",
        description=(
            "URL of a dedicated Skybrush Studio server if you are using a "
            "dedicated server. Leave it empty to use the server provided for "
            "the community for free"
        ),
    )

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "api_key")
        layout.prop(self, "server_url")

        row = layout.row()
        op = row.operator(SetServerURLOperator.bl_idname, text="Use local server")
        op.url = "http://localhost:8000"

        op = row.operator(SetServerURLOperator.bl_idname, text="Use community server")
        op.url = ""

        layout.label(
            text="Restart Blender if you change the settings above.", icon="ERROR"
        )
