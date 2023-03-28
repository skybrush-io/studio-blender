import csv
import logging

from bpy.path import ensure_ext
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from pathlib import Path
from typing import Dict, Tuple
from zipfile import ZipFile

from sbstudio.model.color import Color4D
from sbstudio.model.light_program import LightProgram
from sbstudio.model.point import Point4D
from sbstudio.model.trajectory import Trajectory
from sbstudio.plugin.model.formation import create_formation

__all__ = ("SkybrushCSVImportOperator",)

log = logging.getLogger(__name__)

#############################################################################
# Helper functions for the exporter
#############################################################################


class SkybrushCSVImportOperator(Operator, ImportHelper):
    """Imports Skybrush-compatible .zip compressed .csv files as a new formation."""

    bl_idname = "skybrush.import_csv"
    bl_label = "Import Skybrush CSV"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Skybrush CSV files
    filter_glob = StringProperty(default="*.zip", options={"HIDDEN"})
    filename_ext = ".zip"

    # name under which the new formation will be created
    formation_name = StringProperty(default="Formation from CSV", options={"HIDDEN"})

    def execute(self, context):
        """Executes the Skybrush import procedure."""
        filepath = ensure_ext(self.filepath, self.filename_ext)

        # get trajectories and light program from .zip/.csv files
        try:
            trajectories, light_programs = parse_compressed_csv_zip(filepath, context)
        except RuntimeError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        # create a static formation from the first points
        formation = create_formation(
            self.formation_name,
            [
                trajectory.points[0].as_3d().as_vector()
                for trajectory in trajectories.values()
            ],
        )

        # TODO: add animation to the formation

        # TODO: add light program to the formation

        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


def parse_compressed_csv_zip(
    filename: str, context
) -> Tuple[Dict[str, Trajectory], Dict[str, LightProgram]]:
    """Parse a .zip file containing Skybrush .csv files.

    Parameters:
        filename - the name of the .zip input file
        context - the Blender context

    Returns:
        (trajectories, light_programs) tuple, indexed with the same names.

    Raises:
        RuntimeError on parse errors

    """
    # get framerate and ticks
    fps = context.scene.render.fps

    with ZipFile(filename, "r") as zip_file:
        namelist = zip_file.namelist()
        trajectories = {}
        light_programs = {}
        for filename in namelist:
            name = Path(filename).stem
            if name in trajectories.keys():
                raise RuntimeError(
                    "Duplicate object name in input csv files: {}".format(name)
                )
            with zip_file.open(filename, "r") as csv_file:
                trajectory = Trajectory()
                light_program = LightProgram()
                lines = [line.decode("ascii") for line in csv_file]
                for row in csv.reader(lines, delimiter=","):
                    # skip header line
                    if row[0].lower().startswith("t"):
                        continue
                    # check for errors
                    try:
                        t = float(row[0]) / 1000.0
                        x, y, z = (float(value) for value in row[1:4])
                        if len(row) > 4:
                            r, g, b = (int(value) for value in row[4:7])
                        else:
                            r, g, b = 255, 255, 255
                    except Exception:
                        raise RuntimeError(
                            "Invalid content in input csv file '{}', row {}".format(
                                filename, row
                            )
                        )

                    # store position and color entry
                    trajectory.append(Point4D(t, x, y, z))
                    light_program.append(Color4D(t, r, g, b))

            trajectories[name] = trajectory
            light_programs[name] = light_program

    return (trajectories, light_programs)
