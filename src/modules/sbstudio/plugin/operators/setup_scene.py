from bpy.types import Context, Operator

from sbstudio.plugin.model.led_control import (
    set_expected_3d_viewport_shader_configuration_of_context,
)
from sbstudio.plugin.utils.warnings import get_bad_shader_color_source_warning

__all__ = ("SetupSceneOperator",)


def is_shading_setup_needed(context: Context) -> bool:
    return get_bad_shader_color_source_warning(context) is not None


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
        set_expected_3d_viewport_shader_configuration_of_context(context)

        return {"FINISHED"}
