from bpy.types import PropertyGroup

from sbstudio.plugin.props import ColorProperty

__all__ = ("LEDControlPanelProperties",)


class LEDControlPanelProperties(PropertyGroup):
    primary_color = ColorProperty(
        name="Primary color", description="Primary color to set on the selected drones"
    )
    secondary_color = ColorProperty(
        name="Secondary color",
        description="Secondary color to set on the selected drones; used for gradients only",
        default=(0, 0, 0),
    )

    def swap_colors(self):
        primary, secondary = self.primary_color.copy(), self.secondary_color.copy()
        self.primary_color, self.secondary_color = secondary, primary
