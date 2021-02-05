import bpy

from bpy.props import EnumProperty, StringProperty

from sbstudio.plugin.model.formation import add_objects_to_formation, create_formation

from sbstudio.plugin.utils import propose_name

from .base import FormationOperator
from .update_formation import (
    collect_objects_and_points_for_formation_update,
    get_options_for_formation_update,
    propose_mode_for_formation_update,
)

__all__ = ("CreateFormationOperator",)


class CreateFormationOperator(FormationOperator):
    """Creates a new formation in the Formations collection and adds the
    currently selected vertices to it.
    """

    bl_idname = "skybrush.create_formation"
    bl_label = "Create Formation"
    bl_description = "Creates a new formation in the Formations collection."
    bl_options = {"REGISTER", "UNDO"}

    name = StringProperty(name="Name", description="Name of the new formation")
    contents = EnumProperty(
        name="Initialize with",
        items=get_options_for_formation_update(),
        default="ALL_DRONES",
    )

    works_with_no_selected_formation = True

    def invoke(self, context, event):
        self.name = propose_name("Formation {}", for_collection=True)
        self.contents = propose_mode_for_formation_update(context)
        return context.window_manager.invoke_props_dialog(self)

    def execute_on_formation(self, formation, context):
        bpy.ops.skybrush.prepare()

        name = propose_name(self.name, for_collection=True)
        objects, points = collect_objects_and_points_for_formation_update(self.contents)

        formation = create_formation(name, points)
        add_objects_to_formation(formation, objects)

        self.select_formation(formation, context)

        return {"FINISHED"}
