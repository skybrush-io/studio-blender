from bpy.props import PointerProperty
from bpy.types import PropertyGroup

from .formations_panel import FormationsPanelProperties
from .led_control import LEDControlPanelProperties
from .safety_check import SafetyCheckProperties
from .settings import DroneShowAddonSettings
from .storyboard import Storyboard

__all__ = ("DroneShowAddonProperties",)


class DroneShowAddonProperties(PropertyGroup):
    """Custom Blender property representing the properties of the entire drone
    show addon.

    Each Blender scene that is set up for Skybrush will contain one instance
    of this property.
    """

    formations = PointerProperty(type=FormationsPanelProperties)
    led_control = PointerProperty(type=LEDControlPanelProperties)
    safety_check = PointerProperty(type=SafetyCheckProperties)
    settings = PointerProperty(type=DroneShowAddonSettings)
    storyboard = PointerProperty(type=Storyboard)
