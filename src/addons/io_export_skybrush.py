"""Blender add-on that allows the user to export drone trajectories and light
animation to Skybrush compiled file format (*.skyc).
"""

bl_info = {
    "name": "Export Skybrush Compiled Format (.skyc)",
    "author": "CollMot Robotics Ltd.",
    "description": "Export object trajectories and color animation to Skybrush compiled format",
    "version": (1, 0, 0),
    "blender": (2, 83, 0),
    "location": "File > Export > Skybrush",
    "category": "Import-Export",
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

import logging

from sbstudio.plugin.operators import SkybrushExportOperator
from sbstudio.plugin.plugin_helpers import (
    register_in_menu,
    register_operator,
    unregister_from_menu,
    unregister_operator,
)

#############################################################################
# configure logger

logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
)


#############################################################################
# Boilerplate to register this as an item in the File / Import menu
#############################################################################


def menu_func_export(self, context):
    self.layout.operator(SkybrushExportOperator.bl_idname, text="Skybrush (.skyc)")


def register():
    register_operator(SkybrushExportOperator)
    register_in_menu("File / Export", menu_func_export)


def unregister():
    unregister_operator(SkybrushExportOperator)
    unregister_from_menu("File / Export", menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.object.SkybrushExportOperator("INVOKE_DEFAULT")
