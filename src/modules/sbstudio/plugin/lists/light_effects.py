from __future__ import annotations

from bpy.types import UIList

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bpy.types import Context
    from sbstudio.plugin.model.light_effects import LightEffect

__all__ = ("SKYBRUSH_UL_lightfxlist",)


class SKYBRUSH_UL_lightfxlist(UIList):
    """Customized Blender UI list for light effects."""

    def draw_item(
        self,
        context: Context,
        layout,
        data,
        item: LightEffect,
        icon,
        active_data,
        active_propname,
        index,
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            frame = context.scene.frame_current

            layout.use_property_decorate = False
            layout.alignment = "EXPAND"

            row = layout.row(align=True)

            checkbox = "CHECKBOX_HLT" if item.enabled else "CHECKBOX_DEHLT"
            row.prop(item, "enabled", emboss=False, text="", icon=checkbox)

            row.prop(item, "name", text="", emboss=False)

            if item.contains_frame(frame):
                row.label(
                    text="",
                    translate=False,
                    icon="SEQUENCE_COLOR_04" if item.enabled else "SEQUENCE_COLOR_03",
                )

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"

            checkbox = "CHECKBOX_HLT" if item.enabled else "CHECKBOX_DEHLT"
            layout.prop(item, "enabled", emboss=False, text="", icon=checkbox)
            layout.prop(item, "name", text="", emboss=False)
