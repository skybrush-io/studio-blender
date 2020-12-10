import bpy

from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator
from mathutils import Vector

from sbstudio.plugin.model.formation import create_formation
from sbstudio.plugin.selection import (
    get_selected_objects,
    get_selected_vertices_grouped_by_objects,
    has_selection,
    select_only,
)
from sbstudio.plugin.utils import propose_name

__all__ = ("CreateFormationOperator",)


class CreateFormationOperator(Operator):
    """Creates a new formation in the Formations collection and adds the
    currently selected vertices to it.
    """

    bl_idname = "skybrush.create_formation_from_selection"
    bl_label = "Create Formation"
    bl_description = (
        "Creates a new formation in the Formations collection and optionally "
        "adds the currently selected vertices to it."
    )
    bl_options = {"REGISTER", "UNDO"}

    name = StringProperty(name="Name", description="Name of the new formation")
    contents = EnumProperty(
        name="Initialize with",
        items=[
            ("EMPTY", "Empty", "", 1),
            ("SELECTED_OBJECTS", "Selected objects", "", 2),
            ("SELECTED_VERTICES", "Selected vertices", "", 3),
        ],
        default="SELECTED_VERTICES",
    )

    def execute(self, context):
        # This code path is invoked after an undo-redo
        self._run(context)
        return {"FINISHED"}

    def invoke(self, context, event):
        self.name = propose_name("Formation {}", for_collection=True)
        self.contents = "SELECTED_VERTICES" if has_selection() else "EMPTY"
        return context.window_manager.invoke_props_dialog(self)

    def _run(self, context):
        bpy.ops.skybrush.prepare()

        name = propose_name(self.name, for_collection=True)

        if self.contents == "EMPTY":
            objs_and_points = {}
        elif self.contents == "SELECTED_OBJECTS":
            objs_and_points = {obj: [Vector()] for obj in get_selected_objects()}
        elif self.contents == "SELECTED_VERTICES":
            objs_and_points = {
                obj: [point.co for point in points]
                for obj, points in get_selected_vertices_grouped_by_objects().items()
            }

        points = []
        for obj, points_of_obj in objs_and_points.items():
            local_to_world = obj.matrix_world
            points.extend(local_to_world @ point for point in points_of_obj)

        formation = create_formation(name, points)
        select_only(formation)
