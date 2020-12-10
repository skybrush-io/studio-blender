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

import bpy
import sys

from bpy.path import abspath
from bpy.props import PointerProperty
from bpy.types import Scene
from pathlib import Path


#############################################################################
# Note: This code needs to be harmonized with the plugin installer to have
# the same target directory for all add-on specific dependencies.

candidates = [
    abspath(bpy.context.preferences.filepaths.script_directory),
    Path(sys.modules[__name__].__file__).parent.parent,
]
for candidate in candidates:
    path = (Path(candidate) / "vendor" / "skybrush").resolve()
    if path.exists():
        sys.path.insert(0, str(path))
        break


#############################################################################
# imports needed by the addon

from sbstudio.plugin.model import DroneShow, StoryboardEntry, Storyboard
from sbstudio.plugin.operators import (
    CreateFormationOperator,
    CreateNewStoryboardEntryOperator,
    CreateTakeoffGridOperator,
    PrepareSceneOperator,
    RecalculateTransitionsOperator,
    RemoveStoryboardEntryOperator,
)
from sbstudio.plugin.panels import StoryboardEditor
from sbstudio.plugin.plugin_helpers import (
    register_operator,
    register_panel,
    register_type,
    unregister_operator,
    unregister_panel,
    unregister_type,
)
from sbstudio.plugin.state import (
    register as register_state,
    unregister as unregister_state,
)

#: Custom types in this addon
types = (StoryboardEntry, Storyboard, DroneShow)

#: Operators in this addon; operators that require other operators must come
#: later in the list than their dependencies
operators = (
    PrepareSceneOperator,
    CreateFormationOperator,
    CreateNewStoryboardEntryOperator,
    RemoveStoryboardEntryOperator,
    CreateTakeoffGridOperator,
    RecalculateTransitionsOperator,
)

#: Panels in this addon
panels = (StoryboardEditor,)


def register():
    register_state()
    for custom_type in types:
        register_type(custom_type)
    for operator in operators:
        register_operator(operator)
    for panel in panels:
        register_panel(panel)
    Scene.skybrush = PointerProperty(type=DroneShow)


def unregister():
    for panel in reversed(panels):
        unregister_panel(panel)
    for operator in reversed(operators):
        unregister_operator(operator)
    for custom_type in reversed(types):
        unregister_type(custom_type)
    unregister_state()
