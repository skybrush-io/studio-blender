from bpy.props import IntProperty, PointerProperty
from bpy.types import PropertyGroup

from .formations_panel import FormationsPanelProperties
from .led_control import LEDControlPanelProperties
from .light_effects import LightEffectCollection
from .pyro_control import PyroControlPanelProperties
from .safety_check import SafetyCheckProperties
from .settings import DroneShowAddonFileSpecificSettings
from .storyboard import Storyboard

__all__ = ("DroneShowAddonProperties",)


class DroneShowAddonProperties(PropertyGroup):
    """Custom Blender property representing the properties of the entire drone
    show addon.

    Each Blender scene that is set up for Skybrush will contain one instance
    of this property.
    """

    formations: FormationsPanelProperties = PointerProperty(
        type=FormationsPanelProperties
    )
    led_control: LEDControlPanelProperties = PointerProperty(
        type=LEDControlPanelProperties
    )
    light_effects: LightEffectCollection = PointerProperty(type=LightEffectCollection)
    pyro_control: PyroControlPanelProperties = PointerProperty(
        type=PyroControlPanelProperties
    )
    safety_check: SafetyCheckProperties = PointerProperty(type=SafetyCheckProperties)
    settings: DroneShowAddonFileSpecificSettings = PointerProperty(
        type=DroneShowAddonFileSpecificSettings
    )
    storyboard: Storyboard = PointerProperty(type=Storyboard)
    version: IntProperty = IntProperty(
        name="Version",
        description=(
            "Current version of the show content stored in Blender. "
            "Version 1 is the initial version (plugin version <= 3.13.2). "
            "Version 2 uses a shared material for all drones to speed up light effects."
        ),
        default=1,
    )
