from __future__ import annotations

from bpy.types import Context, UILayout, UIList, bpy_struct

from sbstudio.plugin.model.storyboard import ScheduleOverride

__all__ = ("SKYBRUSH_UL_scheduleoverridelist",)


class SKYBRUSH_UL_scheduleoverridelist(UIList):
    """Customized Blender UI list for transition schedule overrides."""

    def draw_item(
        self,
        context: Context,
        layout: UILayout,
        data: bpy_struct,
        item: ScheduleOverride,
        icon: int,
        active_data: bpy_struct,
        active_propname: str,
        index: int = 0,
        flt_flag: int = 0,
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.use_property_decorate = False
            layout.alignment = "EXPAND"

            checkbox = "CHECKBOX_HLT" if item.enabled else "CHECKBOX_DEHLT"
            layout.prop(item, "enabled", emboss=False, text="", icon=checkbox)
            layout.label(text=item.label)
        elif self.layout_type in {"GRID"}:
            # Removed in Blender 5 but we need to keep it for backward compatibility
            layout.alignment = "CENTER"

            checkbox = "CHECKBOX_HLT" if item.enabled else "CHECKBOX_DEHLT"
            layout.prop(item, "enabled", emboss=False, text="", icon=checkbox)
            layout.label(text=item.label)
