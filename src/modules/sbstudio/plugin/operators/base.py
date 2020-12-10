from bpy.types import Operator


class StoryboardOperator(Operator):
    """Operator mixin that allows an operator to be executed if we have a
    storyboard in the current scene.
    """

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush and context.scene.skybrush.storyboard

    def execute(self, context):
        storyboard = context.scene.skybrush.storyboard
        return self.execute_on_storyboard(storyboard, context)
