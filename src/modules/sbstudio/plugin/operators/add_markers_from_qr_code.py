from bpy.props import EnumProperty, FloatProperty, StringProperty

from numpy import array

from .base import StaticMarkerCreationOperator, PointsAndColors

__all__ = ("AddMarkersFromQRCodeOperator",)


class AddMarkersFromQRCodeOperator(StaticMarkerCreationOperator):
    """Adds new markers to a formation from the shape of a QR code."""

    bl_idname = "skybrush.add_markers_from_qr_code"
    bl_label = "From QR Code"

    bl_description = (
        "Creates a new formation whose points are arranged in the shape of a QR code."
    )
    bl_options = {"REGISTER", "UNDO"}

    text = StringProperty(name="Text", description="Text to embed in the QR code")
    spacing = FloatProperty(
        name="Spacing",
        description="Spacing between the drones in the QR code",
        default=3,
        soft_min=0,
        soft_max=50,
        unit="LENGTH",
    )
    error_correction_level = EnumProperty(
        name="Error correction",
        description="Error correction level to use in the QR code",
        items=[
            ("L", "Level L (7%)", "", 1),
            ("M", "Level M (15%)", "", 2),
            ("Q", "Level Q (25%)", "", 3),
            ("H", "Level H (30%)", "", 4),
        ],
        default="L",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def _create_points(self, context) -> PointsAndColors:
        from sbstudio.vendor.qrcode import (
            QRCode,
            ERROR_CORRECT_L,
            ERROR_CORRECT_M,
            ERROR_CORRECT_Q,
            ERROR_CORRECT_H,
        )

        levels = {
            "L": ERROR_CORRECT_L,
            "M": ERROR_CORRECT_M,
            "H": ERROR_CORRECT_H,
            "Q": ERROR_CORRECT_Q,
        }

        if self.text:
            code = QRCode(error_correction=levels[self.error_correction_level])
            code.add_data(self.text.encode("utf-8", errors="replace"))
            code.make()

            points = array(
                [
                    (0, col_index, -row_index)
                    for row_index, row in enumerate(code.modules)  # type: ignore
                    for col_index, cell in enumerate(row)
                    if cell
                ],
                dtype=float,
            )
        else:
            points = array([], dtype=float)
            points.shape = (0, 3)

        points *= self.spacing

        return PointsAndColors(points)
