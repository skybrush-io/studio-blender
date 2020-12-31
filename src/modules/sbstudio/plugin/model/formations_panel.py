from bpy.types import PropertyGroup

from sbstudio.plugin.props import FormationProperty

__all__ = ("FormationsPanelProperties",)


class FormationsPanelProperties(PropertyGroup):
    selected = FormationProperty(
        description=(
            "Selected formation that the operators in this panel will operate on"
        ),
    )
