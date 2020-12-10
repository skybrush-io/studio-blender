from bpy.props import PointerProperty
from bpy.types import PropertyGroup

from .storyboard import Storyboard

__all__ = ("DroneShow",)


class DroneShow(PropertyGroup):
    """Custom Blender property representing the entire drone show.

    Each Blender scene that is set up for Skybrush will contain one instance
    of this property.
    """

    storyboard = PointerProperty(type=Storyboard)
