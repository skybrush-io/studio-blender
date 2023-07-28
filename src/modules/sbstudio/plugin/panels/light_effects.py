import bpy
from bpy.types import Panel

from sbstudio.plugin.model.light_effects import (
    output_type_supports_mapping_mode,
)
from sbstudio.plugin.operators import (
    CreateLightEffectOperator,
    DuplicateLightEffectOperator,
    MoveLightEffectDownOperator,
    MoveLightEffectUpOperator,
    RemoveLightEffectOperator,
)


class LightEffectsPanel(Panel):
    """Custom Blender panel that allows the user to specify the list of light
    effects that are calculated on-demand when navigating to the appropriate
    frames (instead of using keyframes).
    """

    bl_idname = "OBJECT_PT_LightEffectsPanel"
    bl_label = "Light Effects"

    # The following three settings determine that the light effects panel gets
    # added to the sidebar of the 3D view
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LEDs"

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush.light_effects

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        light_effects = scene.skybrush.light_effects
        if not light_effects:
            return

        row = layout.row()

        col = row.column()
        col.template_list(
            "SKYBRUSH_UL_lightfxlist",
            "OBJECT_PT_skybrush_light_effects_panel",
            light_effects,
            "entries",
            light_effects,
            "active_entry_index",
        )

        col = row.column(align=True)
        col.operator(CreateLightEffectOperator.bl_idname, icon="ADD", text="")
        col.operator(RemoveLightEffectOperator.bl_idname, icon="REMOVE", text="")
        col.separator()
        col.operator(DuplicateLightEffectOperator.bl_idname, icon="DUPLICATE", text="")
        col.separator()
        col.operator(MoveLightEffectUpOperator.bl_idname, icon="TRIA_UP", text="")
        col.operator(MoveLightEffectDownOperator.bl_idname, icon="TRIA_DOWN", text="")

        #####################################################################

        entry = light_effects.active_entry
        if entry is not None:
            layout.prop(entry, "type")

            if entry.texture:
                if entry.type == "COLOR_RAMP":
                    row = layout.box()
                    row.template_color_ramp(entry.texture, "color_ramp")
                elif entry.type == "IMAGE":
                    row = layout.row()

                    col = row.column()
                    col.prop_search(entry.texture, "image", bpy.data, "images", text="")

                    col = row.column(align=True)
                    col.operator("image.open", icon="FILE_FOLDER", text="")
                else:
                    row = layout.box()
                    row.alert = True
                    row.label(
                        text="Invalid light effect type",
                        icon="ERROR",
                    )
                    layout.separator()

            col = layout.column()
            col.prop(entry, "frame_start")
            col.prop(entry, "duration")
            col.separator()
            col.prop(entry, "fade_in_duration")
            col.prop(entry, "fade_out_duration")
            col.separator()
            col.prop(entry, "mesh")
            col.separator()
            col.prop(entry, "output")
            if output_type_supports_mapping_mode(entry.output):
                col.prop(entry, "output_mapping_mode")
            if entry.type == "IMAGE":
                col.prop(entry, "output_y")
                if output_type_supports_mapping_mode(entry.output_y):
                    col.prop(entry, "output_mapping_mode_y")
            col.prop(entry, "target")
            col.prop(entry, "blend_mode")
            col.prop(entry, "influence", slider=True)
            col.prop(entry, "randomness", slider=True)
