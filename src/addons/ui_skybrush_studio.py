bl_info = {
    "name": "Skybrush Studio",
    "author": "CollMot Robotics Ltd.",
    "description": "Extends Blender with UI components for drone show design",
    "version": (1, 0, 0),
    "blender": (2, 83, 0),
    "category": "Interface",
}

#############################################################################
# imports needed to set up the Python path properly

import sys

from bpy.props import PointerProperty
from bpy.types import Scene
from pathlib import Path


#############################################################################
# Note: This code needs to be harmonized with the plugin installer to have
# the same target directory for all add-on specific dependencies.

candidates = [
    Path(sys.modules[__name__].__file__).parent,
    Path(sys.modules[__name__].__file__).parent.parent,
]
for candidate in candidates:
    path = (Path(candidate) / "vendor" / "skybrush").resolve()
    if path.exists():
        sys.path.insert(0, str(path))
        break


#############################################################################
# imports needed by the addon

from sbstudio.plugin.model import (
    DroneShowAddonFileSpecificSettings,
    DroneShowAddonGlobalSettings,
    DroneShowAddonProperties,
    FormationsPanelProperties,
    LEDControlPanelProperties,
    SafetyCheckProperties,
    StoryboardEntry,
    Storyboard,
)
from sbstudio.plugin.operators import (
    ApplyColorsToSelectedDronesOperator,
    CreateFormationOperator,
    CreateNewStoryboardEntryOperator,
    CreateTakeoffGridOperator,
    DetachMaterialsFromDroneTemplateOperator,
    PrepareSceneOperator,
    RecalculateTransitionsOperator,
    RemoveFormationOperator,
    RemoveStoryboardEntryOperator,
    SwapColorsInLEDControlPanelOperator,
    UpdateFormationOperator,
    ValidateTrajectoriesOperator,
)
from sbstudio.plugin.panels import (
    ExportPanel,
    FormationsPanel,
    StoryboardEditor,
    LEDControlPanel,
    SafetyCheckPanel,
)
from sbstudio.plugin.plugin_helpers import (
    register_header,
    register_operator,
    register_panel,
    register_type,
    unregister_header,
    unregister_operator,
    unregister_panel,
    unregister_type,
)
from sbstudio.plugin.state import (
    register as register_state,
    unregister as unregister_state,
)
from sbstudio.plugin.tasks import InitializationTask, SafetyCheckTask


#: Custom types in this addon
types = (
    FormationsPanelProperties,
    StoryboardEntry,
    Storyboard,
    LEDControlPanelProperties,
    SafetyCheckProperties,
    DroneShowAddonFileSpecificSettings,
    DroneShowAddonGlobalSettings,
    DroneShowAddonProperties,
)

#: Operators in this addon; operators that require other operators must come
#: later in the list than their dependencies
operators = (
    PrepareSceneOperator,
    CreateFormationOperator,
    UpdateFormationOperator,
    RemoveFormationOperator,
    CreateNewStoryboardEntryOperator,
    RemoveStoryboardEntryOperator,
    CreateTakeoffGridOperator,
    DetachMaterialsFromDroneTemplateOperator,
    RecalculateTransitionsOperator,
    ApplyColorsToSelectedDronesOperator,
    SwapColorsInLEDControlPanelOperator,
    ValidateTrajectoriesOperator,
)

#: Panels in this addon. The order also implicitly defines the order in which
#: our tabs appear in the sidebar of the 3D view.
panels = (
    FormationsPanel,
    StoryboardEditor,
    LEDControlPanel,
    SafetyCheckPanel,
    ExportPanel,
)

#: Headers in this addon
headers = ()

#: Background tasks in this addon
tasks = (InitializationTask(), SafetyCheckTask())


def register():
    register_state()
    for custom_type in types:
        register_type(custom_type)
    for operator in operators:
        register_operator(operator)
    for panel in panels:
        register_panel(panel)
    for header in headers:
        register_header(header)
    for task in tasks:
        task.register()
    Scene.skybrush = PointerProperty(type=DroneShowAddonProperties)


def unregister():
    for task in tasks:
        task.unregister()
    for header in reversed(headers):
        unregister_header(header)
    for panel in reversed(panels):
        unregister_panel(panel)
    for operator in reversed(operators):
        unregister_operator(operator)
    for custom_type in reversed(types):
        unregister_type(custom_type)
    unregister_state()
