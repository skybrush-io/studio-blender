import csv
import logging

from dataclasses import dataclass
from typing import Dict

from bpy.path import ensure_ext
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from sbstudio.model.color import Color3D
from sbstudio.model.point import Point3D

from sbstudio.plugin.model.formation import add_points_to_formation

from .base import FormationOperator

__all__ = ("AddMarkersFromStaticCSVOperator",)

log = logging.getLogger(__name__)

#############################################################################
# Helper functions for the importer
#############################################################################


@dataclass
class ImportedData:
    position: Point3D
    color: Color3D


class AddMarkersFromStaticCSVOperator(FormationOperator, ImportHelper):
    """Adds markers from a Skybrush-compatible static .csv file (containing a
    single formation snapshot) to the currently selected formation.
    """

    bl_idname = "skybrush.add_markers_from_static_csv"
    bl_label = "Import Skybrush static CSV"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Skybrush static CSV files
    filter_glob = StringProperty(default="*.csv", options={"HIDDEN"})
    filename_ext = ".csv"

    def execute_on_formation(self, formation, context):
        filepath = ensure_ext(self.filepath, self.filename_ext)

        # get positions and colors from a .csv file
        try:
            imported_data = parse_static_csv_zip(filepath, context)
        except RuntimeError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        # create new markers for the points
        points = [item.position.as_vector() for item in imported_data.values()]
        if not points:
            self.report({"ERROR"}, "Formation would be empty, nothing was created")
        else:
            add_points_to_formation(formation, points)

        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


def parse_static_csv_zip(filename: str, context) -> Dict[str, ImportedData]:
    """Parse a Skybrush static .csv file (containing a list of static positions
    and colors)

    Args:
        filename: the name of the .csv input file
        context: the Blender context

    Returns:
        dictionary mapping the imported object names to the corresponding
        position and color

    Raises:
        RuntimeError: on parse errors
    """
    result: Dict[str, ImportedData] = {}
    header_passed: bool = False

    with open(filename, "r") as csv_file:
        lines = list(csv_file)
        for row in csv.reader(lines, delimiter=","):
            # skip empty lines
            if not row:
                continue
            # skip possible header line (starting with "Name")
            if not header_passed:
                header_passed = True
                if row[0].lower().startswith("name"):
                    continue
            # parse line and check for errors
            try:
                name = row[0]
                x, y, z = (float(value) for value in row[1:4])
                if len(row) > 4:
                    r, g, b = (int(value) for value in row[4:7])
                else:
                    r, g, b = 255, 255, 255
                header_passed = True
            except Exception:
                raise RuntimeError(
                    f"Invalid content in input CSV file {filename!r}, row {row!r}"
                ) from None

            # check name
            if name in result:
                raise RuntimeError(f"Duplicate object name in input CSV file: {name}")

            # store position and color entry
            data = ImportedData(position=Point3D(x, y, z), color=Color3D(r, g, b))
            print(data)
            result[name] = data

    return result
