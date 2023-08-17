from bpy.types import UIList

from sbstudio.plugin.model.storyboard import ScheduleOverride

__all__ = ("SKYBRUSH_UL_scheduleoverridelist",)


class SKYBRUSH_UL_scheduleoverridelist(UIList):
    """Customized Blender UI list for transition schedule overrides."""

    def draw_item(
        self,
        context,
        layout,
        data,
        item: ScheduleOverride,
        icon,
        active_data,
        active_propname,
        index,
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.use_property_decorate = False
            layout.alignment = "EXPAND"

            checkbox = "CHECKBOX_HLT" if item.enabled else "CHECKBOX_DEHLT"
            layout.prop(item, "enabled", emboss=False, text="", icon=checkbox)
            layout.label(text=item.label)
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"

            checkbox = "CHECKBOX_HLT" if item.enabled else "CHECKBOX_DEHLT"
            layout.prop(item, "enabled", emboss=False, text="", icon=checkbox)
            layout.label(text=item.label)
