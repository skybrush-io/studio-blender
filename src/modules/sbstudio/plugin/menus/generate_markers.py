from bpy.types import Menu

__all__ = ("GenerateMarkersMenu",)


class GenerateMarkersMenu(Menu):
    """Generates formations from a ZIP of CSV files, a QR code, a mathematical
    expression or something similar"""

    bl_label = "Generate Markers"
    bl_idname = "OBJECT_MT_skybrush_generate_markers"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "skybrush.add_markers_from_static_csv",
            text="From static CSV file",
        )
        layout.operator(
            "skybrush.add_markers_from_zipped_csv",
            text="From zipped CSV files",
        )
        layout.operator(
            "skybrush.add_markers_from_svg",
            text="From SVG file",
        )
        layout.operator("skybrush.add_markers_from_qr_code", text="From QR Code")

    @classmethod
    def poll(cls, context):
        return (
            context.scene.skybrush
            and context.scene.skybrush.formations
            and context.scene.skybrush.formations.selected
        )
