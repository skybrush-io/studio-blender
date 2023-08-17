from bpy.types import UIList

__all__ = ("SKYBRUSH_UL_lightfxlist",)


class SKYBRUSH_UL_lightfxlist(UIList):
    """Customized Blender UI list for light effects."""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.use_property_decorate = False
            layout.alignment = "EXPAND"

            checkbox = "CHECKBOX_HLT" if item.enabled else "CHECKBOX_DEHLT"
            layout.prop(item, "enabled", emboss=False, text="", icon=checkbox)
            layout.prop(item, "name", text="", emboss=False)
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"

            checkbox = "CHECKBOX_HLT" if item.enabled else "CHECKBOX_DEHLT"
            layout.prop(item, "enabled", emboss=False, text="", icon=checkbox)
            layout.prop(item, "name", text="", emboss=False)
