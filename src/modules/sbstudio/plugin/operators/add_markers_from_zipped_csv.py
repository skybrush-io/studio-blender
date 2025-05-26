import csv
import logging

from pathlib import Path
from zipfile import ZipFile

from typing import IO

from bpy.path import ensure_ext
from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from sbstudio.model.color import Color4D
from sbstudio.model.point import Point4D

from .base import DynamicMarkerCreationOperator, TrajectoryAndLightProgram

__all__ = ("AddMarkersFromZippedCSVOperator", "parse_compressed_csv_zip")

log = logging.getLogger(__name__)

#############################################################################
# Helper functions for the importer
#############################################################################


class AddMarkersFromZippedCSVOperator(DynamicMarkerCreationOperator, ImportHelper):
    """Adds markers from Skybrush-compatible .zip compressed dynamic .csv files
    (each containing baked animation of a single drone) to the currently
    selected formation.
    """

    bl_idname = "skybrush.add_markers_from_zipped_csv"
    bl_label = "Import Skybrush zipped CSV"
    bl_options = {"REGISTER", "UNDO"}

    update_duration = BoolProperty(
        name="Update duration of formation",
        default=True,
        description="Update the duration of the storyboard entry based on animation length",
    )

    # List of file extensions that correspond to Skybrush CSV files
    filter_glob = StringProperty(default="*.zip", options={"HIDDEN"})
    filename_ext = ".zip"

    def _create_trajectories(self, context) -> dict[str, TrajectoryAndLightProgram]:
        filepath = ensure_ext(self.filepath, self.filename_ext)
        return parse_compressed_csv_zip(filepath)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


def parse_compressed_csv_zip(
    filename: str | IO[bytes],
) -> dict[str, TrajectoryAndLightProgram]:
    """Parse a .zip file containing Skybrush .csv files (one file per drone,
    each containing baked animation with timestamped positions and colors).

    Args:
        filename: the name of the .zip input file

    Returns:
        dictionary mapping the imported object names to the corresponding
        timestamps, positions and colors

    Raises:
        RuntimeError: on parse errors
    """
    result: dict[str, TrajectoryAndLightProgram] = {}

    with ZipFile(filename, "r") as zip_file:
        for filename in zip_file.namelist():
            name = Path(filename).stem
            if name in result:
                raise RuntimeError(f"Duplicate object name in input CSV files: {name}")

            data = TrajectoryAndLightProgram()
            header_passed: bool = False

            timestamps = data.timestamps
            trajectory = data.trajectory
            light_program = data.light_program

            with zip_file.open(filename, "r") as csv_file:
                lines = [line.decode("ascii") for line in csv_file]
                for row in csv.reader(lines, delimiter=","):
                    # skip empty lines
                    if not row:
                        continue
                    # skip possible header line (starting with "Time_msec")
                    if not header_passed:
                        header_passed = True
                        first_token = row[0].lower()
                        if first_token.startswith(
                            "time_msec"
                        ) or first_token.startswith("time [msec]"):
                            continue
                    # parse line and check for errors
                    try:
                        t = float(row[0]) / 1000.0
                        x, y, z = (float(value) for value in row[1:4])
                        if len(row) > 4:
                            r, g, b = (int(value) for value in row[4:7])
                        else:
                            r, g, b = 255, 255, 255
                    except Exception:
                        raise RuntimeError(
                            f"Invalid content in input CSV file {filename!r}, row {row!r}"
                        ) from None

                    # store position and color entry
                    timestamps.append(t)
                    trajectory.append(Point4D(t, x, y, z))
                    light_program.append(Color4D(t, r, g, b))

            # store the result only if there is at least one point, otherwise
            # there's nothing we can construct
            if timestamps:
                result[name] = data

    return result
