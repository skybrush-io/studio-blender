from bpy.types import Panel

from sbstudio.plugin.operators.create_formation import CreateFormationOperator
from sbstudio.plugin.operators.remove_formation import RemoveFormationOperator
from sbstudio.plugin.operators.update_formation import UpdateFormationOperator

__all__ = ("FormationsPanel",)


class FormationsPanel(Panel):
    """Custom Blender panel that allows the user to create new formations or
    update existing ones.
    """

    bl_idname = "OBJECT_PT_skybrush_formations_panel"
    bl_label = "Formations"

    # The following three settings determine that the Formations panel gets
    # added to the sidebar of the 3D view
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Show Design"

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush.formations

    def draw(self, context):
        scene = context.scene
        formations = scene.skybrush.formations
        if not formations:
            return

        layout = self.layout

        layout.operator(CreateFormationOperator.bl_idname, icon="ADD")

        layout.separator()

        layout.prop(formations, "selected", text="")

        row = layout.row()
        row.operator(
            UpdateFormationOperator.bl_idname, text="Update", icon="RECOVER_LAST"
        )
        row.operator(RemoveFormationOperator.bl_idname, text="Remove", icon="REMOVE")
