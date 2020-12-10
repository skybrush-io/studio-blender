"""Blender operator that prepares a Blender file to be used with the
Skybrush Studio plugin.
"""

from bpy.types import Operator

from sbstudio.plugin.constants import Collections, Templates
from sbstudio.plugin.objects import link_object_to_scene
from sbstudio.plugin.state import get_file_specific_state

__all__ = ("PrepareSceneOperator",)


class PrepareSceneOperator(Operator):
    """Blender operator that prepares a Blender file to be used with the
    Skybrush Studio plugin.

    This involves:

    * creating the standard "Drones" and "Formations" collections if they do not
      exist yet
    * creating a drone
    """

    # TODO(ntamas): make this operator internal!

    bl_idname = "skybrush.prepare"
    bl_label = "Prepare scene for Skybrush"
    # bl_options = {"INTERNAL"}

    def execute(self, context):
        get_file_specific_state().ensure_initialized()

        # Initialize collections
        drones = Collections.find_drones()
        formations = Collections.find_formations()
        templates = Collections.find_templates()

        link_object_to_scene(drones)
        link_object_to_scene(formations)
        link_object_to_scene(templates)

        # Create the drone template as well
        Templates.find_drone()

        return {"FINISHED"}
