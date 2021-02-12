import bpy

from bpy.props import FloatProperty

from sbstudio.plugin.constants import Collections

from .base import StoryboardOperator

__all__ = ("LandOperator",)


class LandOperator(StoryboardOperator):
    """Blender operator that adds a landing transition to the show, starting at
    the current frame.
    """

    bl_idname = "skybrush.land"
    bl_label = "Land Drones"
    bl_description = "Add a landing maneuver to all the drones"
    bl_options = {"REGISTER", "UNDO"}

    only_with_valid_storyboard = True

    altitude = FloatProperty(
        name="Altitude",
        description="Altitude to land to",
        default=0,
        soft_min=-50,
        soft_max=50,
        unit="LENGTH",
    )

    velocity = FloatProperty(
        name="Velocity",
        description="Average vertical velocity during the landing maneuver",
        default=1,
        min=0.1,
        soft_min=0.1,
        soft_max=10,
        unit="VELOCITY",
    )

    @classmethod
    def poll(cls, context):
        # TODO(ntamas): remove when this is implemented!
        return False

        if not super(cls, LandOperator).poll(context):
            return False

        drones = Collections.find_drones(create=False)
        return drones is not None and len(drones.objects) > 0

    def invoke(self, context, event):
        self.start_frame = context.scene.frame_current
        return context.window_manager.invoke_props_dialog(self)

    def execute_on_storyboard(self, storyboard, entries, context):
        return {"FINISHED"} if self._run(context) else {"CANCELLED"}

    def _run(self, context):
        bpy.ops.skybrush.prepare()
        return False
