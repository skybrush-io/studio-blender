from bpy.props import EnumProperty

from .base import StoryboardOperator

__all__ = ("MoveStoryboardEntryDownOperator", "MoveStoryboardEntryUpOperator")


class MoveStoryboardEntryDownOperator(StoryboardOperator):
    """Blender operator that moves the selected storyboard entry one slot down
    in the storyboard.
    """

    bl_idname = "skybrush.move_storyboard_entry_down"
    bl_label = "Move Selected Storyboard Entry Down"
    bl_description = "Moves the selected entry down by one slot in the storyboard"

    @classmethod
    def poll(cls, context):
        if not StoryboardOperator.poll(context):
            return False

        storyboard = context.scene.skybrush.storyboard
        if storyboard.active_entry is None:
            return False

        return (
            storyboard.active_entry is not None
            and storyboard.active_entry_index < len(storyboard.entries) - 1
        )

    def execute_on_storyboard(self, storyboard, context):
        storyboard.move_active_entry_down()
        return {"FINISHED"}


class MoveStoryboardEntryUpOperator(StoryboardOperator):
    """Blender operator that moves the selected storyboard entry one slot up
    in the storyboard.
    """

    bl_idname = "skybrush.move_storyboard_entry_up"
    bl_label = "Move Selected Storyboard Entry Up"
    bl_description = "Moves the selected entry up by one slot in the storyboard"

    @classmethod
    def poll(cls, context):
        if not StoryboardOperator.poll(context):
            return False

        storyboard = context.scene.skybrush.storyboard
        if storyboard.active_entry is None:
            return False

        return storyboard.active_entry is not None and storyboard.active_entry_index > 0

    def execute_on_storyboard(self, storyboard, context):
        storyboard.move_active_entry_up()
        return {"FINISHED"}
