from __future__ import annotations

from typing import Optional

from bpy.props import BoolProperty
from bpy.types import Context, PropertyGroup

from sbstudio.plugin.overlays import FormationOrderOverlay
from sbstudio.plugin.props import FormationProperty

__all__ = ("FormationsPanelProperties",)


_formation_order_overlay = FormationOrderOverlay()
"""Overlay that shows the order of markers in the current formation."""


def get_overlay() -> FormationOrderOverlay:
    return _formation_order_overlay


def order_overlay_enabled_updated(
    self: "FormationsPanelProperties", context: Optional[Context] = None
):
    """Called when user toggles the visibility of the formation order overlay."""
    _formation_order_overlay.enabled = self.order_overlay_enabled


class FormationsPanelProperties(PropertyGroup):
    selected = FormationProperty(
        description=(
            "Selected formation that the operators in this panel will operate on"
        ),
    )

    order_overlay_enabled = BoolProperty(
        name="Show order of markers",
        description=(
            "Shows the order of the markers of the current formation in the 3D view"
        ),
        default=False,
        update=order_overlay_enabled_updated,
    )
