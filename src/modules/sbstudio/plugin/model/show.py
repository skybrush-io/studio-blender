from bpy.props import PointerProperty
from bpy.types import PropertyGroup

from .formations_panel import FormationsPanelProperties
from .led_control import LEDControlPanelProperties
from .light_effects import LightEffectCollection
from .safety_check import SafetyCheckProperties
from .settings import DroneShowAddonFileSpecificSettings
from .storyboard import Storyboard
from .tethers import TetherProperties

__all__ = ("DroneShowAddonProperties",)


class DroneShowAddonProperties(PropertyGroup):
    """Custom Blender property representing the properties of the entire drone
    show addon.

    Each Blender scene that is set up for Skybrush will contain one instance
    of this property.
    """

    formations = PointerProperty(type=FormationsPanelProperties)
    led_control = PointerProperty(type=LEDControlPanelProperties)
    light_effects = PointerProperty(type=LightEffectCollection)
    safety_check = PointerProperty(type=SafetyCheckProperties)
    settings = PointerProperty(type=DroneShowAddonFileSpecificSettings)
    storyboard = PointerProperty(type=Storyboard)
    tethers = PointerProperty(type=TetherProperties)
