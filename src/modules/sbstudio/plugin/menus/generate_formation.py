from bpy.types import Menu


class GenerateFormationMenu(Menu):
    """Generates formations from a ZIP of CSV files, a QR code, a mathematical
    expression or something similar
    """

    bl_label = "Generate Formation"
    bl_idname = "OBJECT_MT_skybrush_generate_formation"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "skybrush.add_markers_from_zipped_csv",
            text="From zipped CSV files",
        )
        # layout.operator("skybrush.generate_formation_from_qr_code", text="From QR Code")

    @classmethod
    def poll(cls, context):
        return (
            context.scene.skybrush
            and context.scene.skybrush.formations
            and context.scene.skybrush.formations.selected
        )
