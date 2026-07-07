from bpy.types import Operator

from sbstudio.plugin.constants import Collections, TakeoffPods
from sbstudio.plugin.objects import link_object_to_scene
from sbstudio.plugin.state import get_file_specific_state

__all__ = ("PrepareSceneOperator",)


class PrepareSceneOperator(Operator):
    """Blender operator that prepares a Blender file to be used with
    Skybrush Studio for Blender.

    This involves creating the standard "Drones", "Formations", "Takeoff pods"
    and "Templates" collections if they do not exist yet, and generating the
    predefined takeoff pods.

    Note that the drone template is not created here yet, only on takeoff grid
    creation later, as it might depend on some user-specified settings.
    """

    bl_idname = "skybrush.prepare"
    bl_label = "Prepare scene for Skybrush"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        get_file_specific_state().ensure_initialized()

        # Initialize collections
        drones = Collections.find_drones()
        formations = Collections.find_formations()
        takeoff_pods = Collections.find_takeoff_pods()
        templates = Collections.find_templates()

        link_object_to_scene(drones, allow_nested=True)
        link_object_to_scene(formations, allow_nested=True)
        link_object_to_scene(takeoff_pods, allow_nested=True)
        link_object_to_scene(templates, allow_nested=True)

        # generate takeoff pods (if they are not generated already)
        TakeoffPods.create_takeoff_pods()

        # Note that we do not create the drone template here yet as
        # its size might depend on later takeoff grid parameters

        return {"FINISHED"}
