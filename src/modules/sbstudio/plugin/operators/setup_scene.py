from typing import cast

from bpy.types import Context, Operator, SpaceView3D

__all__ = ("SetupSceneOperator",)


def is_shading_setup_needed(context: Context) -> bool:
    space = context.space_data
    if not space or space.type != "VIEW_3D":
        return False

    space = cast(SpaceView3D, space)
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
        space = context.space_data
        if space and space.type == "VIEW_3D":
            space = cast(SpaceView3D, space)
            shading = space.shading
            shading.color_type = "OBJECT"
            shading.wireframe_color_type = "OBJECT"

        return {"FINISHED"}
