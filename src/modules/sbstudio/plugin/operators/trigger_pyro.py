from math import degrees, radians

from bpy.props import FloatProperty, IntProperty, StringProperty
from bpy.types import Operator

from sbstudio.model.pyro_markers import PyroMarker, PyroPayload
from sbstudio.plugin.constants import NUM_PYRO_CHANNELS
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

    channel = IntProperty(
        name="Channel",
        description="The (1-based) channel index the pyro is attached to",
        min=1,
        max=NUM_PYRO_CHANNELS,
    )

    name = StringProperty(
        name="Name",
        description="Descriptor of the pyro effect to trigger",
    )

    duration = FloatProperty(
        name="Duration",
        description="The duration of the pyro effect",
        default=30,
        min=0,
        unit="TIME",
        step=100,  # button step is 1/100th of step
    )

    prefire_time = FloatProperty(
        name="Prefire time",
        description="The time needed for the pyro effect to show up after it gets triggered",
        min=0,
        unit="TIME",
        step=100,  # button step is 1/100th of step
    )

    yaw = FloatProperty(
        name="Yaw",
        description="The yaw (pan) angle of the payload, relative to the body frame of the drone",
        default=radians(0),
        soft_min=radians(-180),
        soft_max=radians(180),
        step=100,  # Note that while min and max are expressed in radians, step must be expressed in 100*degrees to work properly
        unit="ROTATION",
    )

    pitch = FloatProperty(
        name="Pitch",
        description="The pitch (tilt) angle of the payload, relative to the body frame of the drone",
        default=radians(-90),
        soft_min=radians(-180),
        soft_max=radians(180),
        step=100,  # Note that while min and max are expressed in radians, step must be expressed in 100*degrees to work properly
        unit="ROTATION",
    )

    def execute(self, context):
        # This code path is invoked after an undo-redo
        return {"FINISHED"} if self._run(context) else {"CANCELLED"}

    def invoke(self, context, event):
        # Inherit properties from the Pyro control panel
        pyro_control = context.scene.skybrush.pyro_control

        self.channel = pyro_control.channel
        self.name = pyro_control.name
        self.duration = pyro_control.duration
        self.prefire_time = pyro_control.prefire_time
        self.yaw = pyro_control.yaw
        self.pitch = pyro_control.pitch

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
            self.report({"ERROR"}, "Select some drones first to trigger pyro")
            return False

        frame = context.scene.frame_current
        for drone in selection:
            self._trigger_pyro_on_single_drone(drone, frame)

        return True

    def _trigger_pyro_on_single_drone(self, drone, frame: int):
        add_pyro_marker_to_object(
            drone,
            channel=self.channel,
            marker=PyroMarker(
                frame=frame,
                payload=PyroPayload(
                    name=self.name,
                    duration=self.duration,
                    prefire_time=self.prefire_time,
                    yaw=round(degrees(self.yaw), 3),
                    pitch=round(degrees(self.pitch), 3),
                ),
            ),
        )
