"""Blender add-on that allows the user to open a Skybrush (.sky) file directly
in Blender and let the scene render itself automatically.
"""

bl_info = {
    "name": "Import Skybrush Script Format (.sky)",
    "author": "Tamas Nepusz (CollMot Robotics Ltd.)",
    "description": "Import a Skybrush file directly into Blender",
    "version": (0, 1, 0),
    "blender": (2, 83, 0),
    "location": "File > Import > Skybrush",
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

from bpy_extras.io_utils import ImportHelper
from bpy.path import ensure_ext
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import Operator
from copy import deepcopy

from skybrush.io.sky.runner import SkybrushScriptRunner
from skybrush.io.blender.renderer import render
from skybrush.io.base.renderer import RenderContext, RenderMode
from skybrush.utils.filesystem import working_directory

from sbstudio.plugin.plugin_helpers import (
    register_in_menu,
    register_operator,
    unregister_from_menu,
    unregister_operator,
)


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


def _run_script(filename, context, parameters):
    """Executes a Skybrush script with the given rendering context and
    parameters.

    This is a helper function for the common parts of SkybrushImportOperator_
    and SkybrushReimportOperator_
    """

    log.info(f"import started from '{filename}'")

    runner = SkybrushScriptRunner()
    if "seed" in parameters:
        runner.seed = parameters.pop("seed")

    vars = runner.run(filename)

    log.info("script parsed")

    with working_directory(Path(filename).parent):
        render(vars.get_world(), context, parameters)

    log.info("script rendered, import finished")


#############################################################################
# Operator that allows the user to invoke the import operation
#############################################################################


class SkybrushImportOperator(Operator, ImportHelper):
    """Imports a Skybrush file directly into Blender."""

    bl_idname = "import.skybrush"
    bl_label = "Import Skybrush SKY"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Skybrush files
    filter_glob = StringProperty(default="*.sky", options={"HIDDEN"})
    filename_ext = ".sky"

    # Rendering mode to use when importing the file
    mode = EnumProperty(
        items=[
            (RenderMode.DRAFT.value, "Draft", "Draft rendering (faster)"),
            (
                RenderMode.PRODUCTION.value,
                "Production",
                "Production rendering (slower)",
            ),
        ],
        name="Mode",
        default=RenderMode.DRAFT.value,
        description="Rendering mode to use when executing the Skybrush script",
    )

    # Random seed to use when importing the file
    seed = IntProperty(
        name="Random seed",
        default=0,
        min=0,
        description="Seed value to use when generating random numbers during the execution of the script",
    )

    # amount of glow added to drone objects on render
    glow_strength = FloatProperty(
        name="Glow Strength",
        default=1,
        min=0,
        max=1,
        description="Amount of glow to add to the rendered drone objects",
    )

    # Stores whether the names of the drones and environment items should be
    # shown by default
    show_names = BoolProperty(
        name="Show names",
        default=False,
        description="Show the names of the drones and the environment items in the scene after import",
    )

    # Stores whether the drone trajectories should be shown by default
    show_trajectories = BoolProperty(
        name="Show trajectories",
        default=False,
        description="Show drone trajectories in the scene after import",
    )

    def execute(self, context):
        """Executes the Skybrush import procedure."""
        filepath = ensure_ext(self.filepath, self.filename_ext)
        parameters = {
            "glow_strength": self.glow_strength,
            "seed": self.seed,
            "show_trajectories": self.show_trajectories,
            "show_names": self.show_names,
            "verbose": False,
        }

        context = RenderContext()
        context.mode = self.mode
        context.filename = filepath

        # Make a copy of the context and the parameters before executing the
        # import procedure in case some parameters are mutable and the script
        # modifies them
        parameters_copy = deepcopy(parameters)
        context_copy = deepcopy(context)

        # Notify the reimport operator
        SkybrushReimportOperator.notify_import(filepath, context_copy, parameters_copy)

        # Run the script
        _run_script(filepath, context, parameters)

        return {"FINISHED"}


#############################################################################
# Operator that allows the user to re-run the last import operation
#############################################################################


class SkybrushReimportOperator(Operator):
    """Re-imports the last imported Skybrush file into Blender."""

    bl_idname = "script.skybrush_reimport"
    bl_label = "Reload Skybrush SKY"
    bl_options = {"REGISTER"}

    _last_operation = None

    @classmethod
    def notify_import(cls, filename, context, parameters):
        """Notifies the plugin that a Skybrush script with the given filename,
        context and parameters were imported.
        """
        cls._last_operation = {
            "context": context,
            "filename": filename,
            "parameters": parameters,
        }

    def execute(self, context):
        """Executes the last imported Skybrush script again."""
        cls = self.__class__
        if cls._last_operation:
            _run_script(**cls._last_operation)
        else:
            self.report({"ERROR"}, "No Skybrush file has been imported yet")
        return {"FINISHED"}


#############################################################################
# Boilerplate to register this as an item in the File / Import menu
#############################################################################


def menu_func_import(self, context):
    self.layout.operator(SkybrushImportOperator.bl_idname, text="Skybrush (.sky)")


def register():
    register_operator(SkybrushImportOperator)
    register_operator(SkybrushReimportOperator)
    register_in_menu("File / Import", menu_func_import)


def unregister():
    unregister_operator(SkybrushReimportOperator)
    unregister_operator(SkybrushImportOperator)
    unregister_from_menu("File / Import", menu_func_import)


if __name__ == "__main__":
    register()

    # test calls
    # bpy.ops.object.SkybrushImportOperator("INVOKE_DEFAULT")
    # bpy.ops.object.SkybrushReImportOperator("INVOKE_DEFAULT")
