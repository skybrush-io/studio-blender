from bpy.props import IntProperty, StringProperty
from bpy.types import Operator

from sbstudio.plugin.constants import NUM_PYRO_CHANNELS
from sbstudio.model.pyro_markers import PyroMarker
from sbstudio.plugin.selection import get_selected_drones
from sbstudio.plugin.utils.pyro_markers import add_pyro_marker_to_object

__all__ = ("TriggerPyroOnSelectedDronesOperator",)


class TriggerPyroOnSelectedDronesOperator(Operator):
    """Triggers the defined pyro effect of the Pyro control panel
    on the currently selected drones."""

    bl_idname = "skybrush.trigger_pyro_on_selection"
    bl_label = "Trigger Pyro on Selected Drones"
    bl_description = (
        "Triggers the defined pyro effect of the Pyro control panel "
        "on the currently selected drones"
    )
    bl_options = {"REGISTER", "UNDO"}

    name = StringProperty(
        name="Name",
        description="Unique descriptor of the pyro effect to trigger, in VDL format",
    )

    channel = IntProperty(
        name="Channel",
        description="The channel index the pyro is attached to",
        min=1,
        max=NUM_PYRO_CHANNELS,
    )

    def execute(self, context):
        # This code path is invoked after an undo-redo
        return {"FINISHED"} if self._run(context) else {"CANCELLED"}

    def invoke(self, context, event):
        # Inherit properties from the Pyro control panel
        pyro_control = context.scene.skybrush.pyro_control

        self.name = pyro_control.name
        self.channel = pyro_control.channel

        if event.type == "LEFTMOUSE":
            # We are being invoked from a button in the Pyro control panel.
            # Move on straight to the execution phase.
            return self.execute(context)
        else:
            # We are probably being invoked from the Blender command palette
            # so show the props dialog.
            return context.window_manager.invoke_props_dialog(self)

    def _run(self, context):
        selection = get_selected_drones()
        num_selected = len(selection)
        if not num_selected:
            self.report({"INFO"}, "Select some drones first to trigger pyro")
            return False

        frame = context.scene.frame_current
        for drone in selection:
            self._trigger_pyro_on_single_drone(drone, frame)

        return True

    def _trigger_pyro_on_single_drone(self, drone, frame: int):
        add_pyro_marker_to_object(
            drone,
            channel=self.channel,
            marker=PyroMarker(name=self.name, frame=frame),
        )
