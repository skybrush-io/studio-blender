from bpy.types import Operator

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.objects import (
    ensure_direct_scene_child,
    link_to_scene,
    order_child_collections,
)
from sbstudio.plugin.state import get_file_specific_state

__all__ = ("PrepareSceneOperator",)


class PrepareSceneOperator(Operator):
    """Blender operator that prepares a Blender file to be used with
    Skybrush Studio for Blender.

    This involves creating the standard "Drones", "Drone Groups" and "Formations"
    collections if they do not exist yet.
    """

    bl_idname = "skybrush.prepare"
    bl_label = "Prepare scene for Skybrush"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        get_file_specific_state().ensure_initialized()

        # Initialize collections
        drones = Collections.find_drones()
        drone_groups = Collections.find_drone_groups()
        formations = Collections.find_formations()
        templates = Collections.find_templates()

        link_to_scene(drones, allow_nested=True)
        link_to_scene(formations, allow_nested=True)
        link_to_scene(templates, allow_nested=True)
        # Keep Drone Groups as the last scene-root sibling. Assigning drones into
        # group sub-collections makes the Outliner very tall; if Drone Groups
        # sits above Drones/Formations, those collections get pushed far down.
        ensure_direct_scene_child(drone_groups, scene=context.scene)
        order_child_collections(
            context.scene.collection,
            [drones, formations, templates, drone_groups],
        )

        # Note that we do not create the drone template here yet as
        # its size might depend on later takeoff grid parameters

        return {"FINISHED"}
