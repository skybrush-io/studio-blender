import bpy

from bpy.types import Panel

from sbstudio.plugin.operators import SkybrushExportOperator

__all__ = ("ExportPanel",)


class ExportPanel(Panel):
    """Custom Blender panel that allows the user to export the current show into
    one of the supported formats.
    """

    bl_idname = "OBJECT_PT_skybrush_export_panel"
    bl_label = "Export"

    # The following three settings determine that the Export panel gets
    # added to the sidebar of the 3D view
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Safety & Export"

    def draw(self, context):
        scene = context.scene
        settings = scene.skybrush.settings

        layout = self.layout

        if settings:
            layout.prop(settings, "show_type")

        layout.operator(SkybrushExportOperator.bl_idname, text="Export to .skyc")

        try:
            # Test whether the CSV export operator is registered
            bpy.ops.export_scene.skybrush_csv.get_rna_type()
            layout.operator("export_scene.skybrush_csv", text="Export to .csv")
        except Exception:
            box = layout.box()
            box.label(text="CSV export addon disabled", icon="ERROR")
