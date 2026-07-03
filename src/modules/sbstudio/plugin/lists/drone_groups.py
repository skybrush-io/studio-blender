from __future__ import annotations

from bpy.types import Collection, Context, UILayout, UIList, bpy_struct

__all__ = ("SKYBRUSH_UL_dronegrouplist",)


class SKYBRUSH_UL_dronegrouplist(UIList):
    """Customized Blender UI list for drone groups that also show the group size."""

    def draw_item(
        self,
        context: Context,
        layout: UILayout,
        data: bpy_struct,
        item: Collection,
        icon: int,
        active_data: bpy_struct,
        active_propname: str,
        index: int = 0,
        flt_flag: int = 0,
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.use_property_decorate = False
            layout.alignment = "EXPAND"
        elif self.layout_type in {"GRID"}:
            # Removed in Blender 5 but we need to keep it for backward compatibility
            layout.alignment = "CENTER"

        split = layout.split(factor=0.9)
        split.prop(item, "name", text="", emboss=False, icon="OUTLINER_OB_POINTCLOUD")

        right = split.row()
        right.alignment = "RIGHT"
        right.enabled = False
        right.label(text=str(len(item.objects)), translate=False)
