from bpy.types import Header


class MinimumClearanceIndicator(Header):
    """Custom Blender header widget that shows the minimum clearance between
    all drones in the current frame.
    """

    bl_idname = "OBJECT_HT_skybrush_clearance_indicator"
    bl_label = "Clearance"

    # The following three settings determine that the clearance indicator gets
    # added to the 3D View
    bl_space_type = "VIEW_3D"
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Not implemented yet")
