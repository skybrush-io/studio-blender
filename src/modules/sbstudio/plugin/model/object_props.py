from bpy.props import StringProperty
from bpy.types import PropertyGroup

__all__ = ("DroneShowAddonObjectProperties",)


class DroneShowAddonObjectProperties(PropertyGroup):
    """Custom Blender property representing the extra addon-specific properties
    that we attach to a Blender object.
    """

    formation_vertex_group = StringProperty(
        name="Formation vertex group",
        description="Name of the vertex group designated for containing the vertices that the drones should occupy when their parent object is placed in the storyboard",
        default="",
    )

    pyro_markers = StringProperty(
        name="Pyro markers",
        description="Pyro trigger events associated with an object, stored as a JSON string.",
        default="",
    )
