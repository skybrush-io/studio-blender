import csv
import logging

from numpy import array, zeros
from numpy.typing import NDArray
from typing import Dict, Tuple

from bpy.path import ensure_ext
from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from .base import StaticMarkerCreationOperator, PointsAndColors

__all__ = ("AddMarkersFromStaticCSVOperator",)

log = logging.getLogger(__name__)

#############################################################################
# Helper functions for the importer
#############################################################################


class AddMarkersFromStaticCSVOperator(StaticMarkerCreationOperator, ImportHelper):
    """Adds markers from a Skybrush-compatible static .csv file (containing a
    single formation snapshot) to the currently selected formation.
    """

    bl_idname = "skybrush.add_markers_from_static_csv"
    bl_label = "Import Skybrush static CSV"
    bl_options = {"REGISTER"}

    import_colors = BoolProperty(
        name="Import colors",
        description="Import colors from the CSV file into a light effect",
        default=True,
    )

    # List of file extensions that correspond to Skybrush static CSV files
    filter_glob = StringProperty(default="*.csv", options={"HIDDEN"})
    filename_ext = ".csv"

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def _create_points(self, context) -> PointsAndColors:
        filepath = ensure_ext(self.filepath, self.filename_ext)
        point_color_pairs = parse_static_csv_zip(filepath)

        points = zeros((len(point_color_pairs), 3), dtype=float)
        colors = zeros((len(point_color_pairs), 3), dtype=float) + 1

        for index, (p, c) in enumerate(point_color_pairs.values()):
            points[index, :] = p
            colors[index, :] = c / 255

        return PointsAndColors(points, colors)


Item = Tuple[NDArray[float], NDArray[int]]


def parse_static_csv_zip(filename: str) -> Dict[str, Item]:
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
    result: Dict[str, Item] = {}
    header_passed: bool = False

    with open(filename, "r") as csv_file:
        for row in csv.reader(csv_file, delimiter=","):
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
            result[name] = array((x, y, z), dtype=float), array(
                (r, g, b, 255), dtype=int
            )

    return result
