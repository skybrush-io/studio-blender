from bpy.types import Panel

from sbstudio.plugin.operators import (
    CreateLightEffectOperator,
    MoveLightEffectDownOperator,
    MoveLightEffectUpOperator,
    RemoveLightEffectOperator,
)


class LightEffectsPanel(Panel):
    """Custom Blender panel that allows the user to specify the list of light
    effects that are calculated on-demand when navigating to the appropriate
    frames (instead of using keyframes).
    """

    bl_idname = "OBJECT_PT_skybrush_light_effects_panel"
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
        scene = context.scene
        light_effects = scene.skybrush.light_effects
        if not light_effects:
            return

        layout = self.layout

        layout.use_property_split = True
        # layout.use_property_decorate = False

        row = layout.row()

        col = row.column()
        col.template_list(
            "UI_UL_list",
            "OBJECT_PT_skybrush_light_effects_panel",
            light_effects,
            "entries",
            light_effects,
            "active_entry_index",
            maxrows=10,
            sort_lock=True,
        )

        col = row.column(align=True)
        col.operator(CreateLightEffectOperator.bl_idname, icon="ADD", text="")
        col.operator(RemoveLightEffectOperator.bl_idname, icon="REMOVE", text="")
        col.separator()
        col.operator(MoveLightEffectUpOperator.bl_idname, icon="TRIA_UP", text="")
        col.operator(MoveLightEffectDownOperator.bl_idname, icon="TRIA_DOWN", text="")

        #####################################################################

        entry = light_effects.active_entry
        if entry is not None:
            if entry.texture:
                layout.template_color_ramp(entry.texture, "color_ramp")
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
            col.prop(entry, "influence", slider=True)
            col.prop(entry, "enabled")  # TODO(ntamas): move this to each list item
