from bpy.types import Context, Operator

from sbstudio.plugin.views import find_current_3d_view

__all__ = ("SetupSceneOperator",)


def is_shading_setup_needed(context: Context) -> bool:
    space = find_current_3d_view(context)
    if space is None:
        return False
    shading = space.shading

    return shading.wireframe_color_type != "OBJECT" or shading.color_type != "OBJECT"


def is_setup_needed(context: Context) -> bool:
    return is_shading_setup_needed(context)


class SetupSceneOperator(Operator):
    """Performs basic setup on the current scene to ensure that it is set up according
    to the requirements of the add-on.
    """

    bl_idname = "skybrush.setup_scene"
    bl_label = "Initialize Add-On"
    bl_description = "Initializes the settings of the current scene according to the requirements of the add-on."

    @classmethod
    def poll(self, context: Context) -> bool:
        return is_setup_needed(context)

    def execute(self, context: Context):
        space = find_current_3d_view(context)
        if space is not None:
            shading = space.shading
            shading.color_type = "OBJECT"
            shading.wireframe_color_type = "OBJECT"

        return {"FINISHED"}
