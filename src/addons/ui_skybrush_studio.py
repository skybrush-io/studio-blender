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

from sbstudio.plugin.operators import (
    CreateTakeoffGridOperator,
    PrepareSceneOperator,
)
from sbstudio.plugin.plugin_helpers import register_operator, unregister_operator


#: Operators in this addon; operators that require other operators must come
#: later in the list than their dependencies
operators = (PrepareSceneOperator, CreateTakeoffGridOperator)


def register():
    for operator in operators:
        register_operator(operator)


def unregister():
    for operator in reversed(operators):
        unregister_operator(operator)
