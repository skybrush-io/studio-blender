from bpy.types import Panel

from sbstudio.plugin.operators import (
    TriggerPyroOnSelectedDronesOperator as TriggerPyro,
)


class PyroControlPanel(Panel):
    """Custom Blender panel that allows the user to control trigger events
    for drone-launched fireworks in the current drone show.
    """

    bl_idname = "OBJECT_PT_skybrush_pyro_control_panel"
    bl_label = "Pyro Control"

    # The following three settings determine that the Pyro control panel gets
    # added to the sidebar of the 3D view
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Pyro"

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush.pyro_control

    def draw(self, context):
        scene = context.scene
        pyro_control = scene.skybrush.pyro_control
        if not pyro_control:
            return

        layout = self.layout

        layout.prop(pyro_control, "name")
        layout.prop(pyro_control, "channel")

        layout.separator()

        layout.operator(TriggerPyro.bl_idname, text="Trigger")
