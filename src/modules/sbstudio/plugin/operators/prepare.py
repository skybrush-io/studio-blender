"""Blender operator that prepares a Blender file to be used with the
Skybrush Studio plugin.
"""

import bpy

from bpy.types import Operator

from sbstudio.plugin.utils import (
    ensure_object_exists_in_collection,
    link_object_to_scene,
)

__all__ = ("PrepareSceneOperator",)


class PrepareSceneOperator(Operator):
    """Blender operator that prepares a Blender file to be used with the
    Skybrush Studio plugin.

    This involves:

    * creating the standard "Drones" and "Formations" collections if they do not
      exist yet.
    """

    bl_idname = "skybrush.prepare"
    bl_label = "Prepare scene for Skybrush"
    bl_options = {"REGISTER"}

    def execute(self, context):
        drones = ensure_object_exists_in_collection(bpy.data.collections, "Drones")
        formations = ensure_object_exists_in_collection(
            bpy.data.collections, "Formations"
        )

        link_object_to_scene(drones)
        link_object_to_scene(formations)

        return {"FINISHED"}
