from bpy.props import PointerProperty
from bpy.types import PropertyGroup

from .led_control import LEDControlPanelProperties
from .storyboard import Storyboard

__all__ = ("DroneShowAddonProperties",)


class DroneShowAddonProperties(PropertyGroup):
    """Custom Blender property representing the properties of the entire drone
    show addon.

    Each Blender scene that is set up for Skybrush will contain one instance
    of this property.
    """

    storyboard = PointerProperty(type=Storyboard)
    led_control = PointerProperty(type=LEDControlPanelProperties)
