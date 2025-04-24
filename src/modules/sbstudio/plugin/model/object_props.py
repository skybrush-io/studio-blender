from bpy.props import StringProperty
from bpy.types import Context, PropertyGroup

from sbstudio.plugin.utils.pyro_markers import update_pyro_particles_of_object

__all__ = ("DroneShowAddonObjectProperties",)


def pyro_markers_updated(self, context: Context):
    """Called when the pyro markers got updated by the user."""
    update_pyro_particles_of_object(context.object)


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
        update=pyro_markers_updated,
    )
