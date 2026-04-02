"""Blender add-on that allows the user to open any supported Skybrush format
directly in Blender and let the scene render itself automatically.

Requires the `skybrush-studio` Python module. Contact us if you are interested.
"""

bl_info = {
    "name": "Import All Skybrush-compatible Formats",
    "author": "Gabor Vasarhelyi (CollMot Robotics Ltd.)",
    "description": "Imports a Skybrush-compatible file directly into Blender",
    "version": (0, 1, 0),
    "blender": (4, 4, 0),
    "location": "File > Import > Skybrush",
    "category": "Import-Export",
}

__license__ = "GPLv3"

#############################################################################
# imports needed to set up the Python path properly

import sys
from pathlib import Path

import bpy
from bpy.path import abspath

#############################################################################
# Note: This code needs to be harmonized with the plugin installer to have
# the same target directory for all add-on specific dependencies.

candidates = [
    abspath(script_directory.directory)
    for script_directory in bpy.context.preferences.filepaths.script_directories
]
candidates.append(Path(sys.modules[__name__].__file__).parent.parent)

for candidate in candidates:
    path = (Path(candidate) / "vendor" / "skybrush").resolve()
    if path.exists():
        sys.path.insert(0, str(path))
        break


#############################################################################
# imports needed by the addon

import logging

from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from sbstudio.plugin.plugin_helpers import (
    register_in_menu,
    register_operator,
    unregister_from_menu,
    unregister_operator,
)
from skybrush.io.base.importer import ImportContext, find_importer_function
from skybrush.io.base.renderer import RenderContext, RenderMode
from skybrush.io.blender.renderer import render
from skybrush.io.utils import uncompressed_file_list
from skybrush.utils.filesystem import working_directory

#############################################################################
# configure logger

log = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
)


#############################################################################
# Helper functions for the importer
#############################################################################

importers = {
    "csv": {"suffix": ".zip", "func": "skybrush.io.csv.importer"},
    "sky": {"suffix": ".sky", "func": "skybrush.io.sky.importer"},
    "skyc": {"suffix": ".skyc", "func": "skybrush.io.skyc.importer"},
}


def _run_script(filename, importer_parameters, renderer_parameters):
    """Imports world with the given parameters.

    This is a helper function for SkybrushImportAllOperator_
    """

    log.info(f"import started from '{filename}'")

    # find importer
    suffix = Path(filename).suffix
    for value in importers.values():
        if value["suffix"] == suffix:
            break
    else:
        log.warn(f"No importer found for the given file extention: {suffix}")
        return
    importer = find_importer_function(value["func"])

    # import world
    with uncompressed_file_list([filename]) as inputs:
        context = ImportContext()
        world = importer(inputs, context, importer_parameters)

    log.info("script parsed")

    # render world
    with working_directory(Path(filename).parent):
        context = RenderContext()
        context.mode = RenderMode.DRAFT.value
        # context.filename = filepath
        render(world, context, renderer_parameters)

    log.info("script rendered, import finished")


#############################################################################
# Operator that allows the user to invoke the import operation
#############################################################################


class SkybrushImportAllOperator(Operator, ImportHelper):
    """Imports a Skybrush-compatible file directly into Blender."""

    bl_idname = "import.skybrush_all"
    bl_label = "Import Skybrush ALL"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Skybrush compatible formats
    filter_glob = StringProperty(
        default=";".join(
            ["*{}".format(value["suffix"]) for value in importers.values()]
        ),
        options={"HIDDEN"},
    )
    # filename_ext = ".zip"

    def execute(self, context):
        """Executes the Skybrush import procedure."""
        # filepath = ensure_ext(self.filepath, self.filename_ext)
        filepath = self.filepath
        importer_parameters = {
            "add_takeoff": False,
            "sort_inputs": True,
            "keep_names": True,
        }
        renderer_parameters = {
            "glow_strength": 1,
            "show_trajectories": False,
            "show_names": False,
            "verbose": False,
        }

        # Run the script
        _run_script(filepath, importer_parameters, renderer_parameters)

        return {"FINISHED"}


#############################################################################
# Boilerplate to register this as an item in the File / Import menu
#############################################################################


def menu_func_import(self, context):
    self.layout.operator(
        SkybrushImportAllOperator.bl_idname,
        text="Skybrush-compatible Formats (.sky/.skyc/.zip)",
    )


def register():
    register_operator(SkybrushImportAllOperator)
    register_in_menu("File / Import", menu_func_import)


def unregister():
    unregister_operator(SkybrushImportAllOperator)
    unregister_from_menu("File / Import", menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    # bpy.ops.object.SkybrushImportAllOperator("INVOKE_DEFAULT")
