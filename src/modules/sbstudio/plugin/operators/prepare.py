from bpy.types import Operator

from sbstudio.plugin.constants import Collections, Templates
from sbstudio.plugin.objects import link_object_to_scene
from sbstudio.plugin.state import get_file_specific_state

__all__ = ("PrepareSceneOperator",)


class PrepareSceneOperator(Operator):
    """Blender operator that prepares a Blender file to be used with
    Skybrush Studio for Blender.

    This involves:

    * creating the standard "Drones" and "Formations" collections if they do not
      exist yet
    * creating a drone template and putting it in the "Templates" collection
    """

    bl_idname = "skybrush.prepare"
    bl_label = "Prepare scene for Skybrush"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        get_file_specific_state().ensure_initialized()

        # Initialize collections
        drones = Collections.find_drones()
        formations = Collections.find_formations()
        templates = Collections.find_templates()

        link_object_to_scene(drones, allow_nested=True)
        link_object_to_scene(formations, allow_nested=True)
        link_object_to_scene(templates, allow_nested=True)

        # Create the drone template as well
        Templates.find_drone()

        return {"FINISHED"}
