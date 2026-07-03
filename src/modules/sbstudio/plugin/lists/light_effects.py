from __future__ import annotations

import bpy
from bpy.types import Context, UILayout, UIList, bpy_struct

from sbstudio.plugin.model.light_effects import LightEffect

__all__ = ("SKYBRUSH_UL_lightfxlist",)


class SKYBRUSH_UL_lightfxlist(UIList):
    """Customized Blender UI list for light effects."""

    def draw_item(
        self,
        context: Context,
        layout: UILayout,
        data: bpy_struct,
        item: LightEffect,
        icon: int,
        active_data: bpy_struct,
        active_propname: str,
        index: int = 0,
        flt_flag: int = 0,
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
                item_icon = "SEQUENCE_COLOR_04" if item.enabled else "SEQUENCE_COLOR_03"
                if bpy.app.version >= (4, 4, 0):
                    item_icon = item_icon.replace("SEQUENCE_", "STRIP_")

                row.label(text="", translate=False, icon=item_icon)

        elif self.layout_type in {"GRID"}:
            # Removed in Blender 5 but we need to keep it for backward compatibility
            layout.alignment = "CENTER"

            checkbox = "CHECKBOX_HLT" if item.enabled else "CHECKBOX_DEHLT"
            layout.prop(item, "enabled", emboss=False, text="", icon=checkbox)
            layout.prop(item, "name", text="", emboss=False)
