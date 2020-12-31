from bpy.props import StringProperty
from bpy.types import AddonPreferences

__all__ = ("DroneShowAddonGlobalSettings",)


class DroneShowAddonGlobalSettings(AddonPreferences):
    """Global settings of the Skybrush Studio addon."""

    bl_idname = "ui_skybrush_studio"

    api_key = StringProperty(
        name="API Key",
        description="API Key that is used when communicating with the Skybrush Studio server",
    )

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "api_key")
