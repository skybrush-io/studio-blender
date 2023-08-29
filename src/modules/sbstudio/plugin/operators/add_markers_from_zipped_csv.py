import csv
import logging

from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Dict, List
from zipfile import ZipFile

from bpy.path import ensure_ext
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from sbstudio.model.color import Color4D
from sbstudio.model.point import Point4D
from sbstudio.model.light_program import LightProgram
from sbstudio.model.trajectory import Trajectory
from sbstudio.plugin.actions import (
    ensure_action_exists_for_object,
    find_f_curve_for_data_path_and_index,
)
from sbstudio.plugin.model.formation import add_points_to_formation

from .base import FormationOperator

__all__ = ("AddMarkersFromZippedCSVOperator",)

log = logging.getLogger(__name__)

#############################################################################
# Helper functions for the importer
#############################################################################


@dataclass
class ImportedData:
    timestamps: List[float] = field(default_factory=list)
    trajectory: Trajectory = field(default_factory=Trajectory)
    light_program: LightProgram = field(default_factory=LightProgram)


class AddMarkersFromZippedCSVOperator(FormationOperator, ImportHelper):
    """Adds markers from Skybrush-compatible .zip compressed dynamic .csv files
    (each containing baked animation of a single drone) to the currently
    selected formation.
    """

    bl_idname = "skybrush.add_markers_from_zipped_csv"
    bl_label = "Import Skybrush zipped CSV"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Skybrush CSV files
    filter_glob = StringProperty(default="*.zip", options={"HIDDEN"})
    filename_ext = ".zip"

    def execute_on_formation(self, formation, context):
        filepath = ensure_ext(self.filepath, self.filename_ext)

        # get trajectories and light program from .zip/.csv files
        try:
            imported_data = parse_compressed_csv_zip(filepath, context)
        except RuntimeError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        # determine FPS of scene
        fps = context.scene.render.fps

        # try to figure out the start frame of this formation
        storyboard_entry = (
            context.scene.skybrush.storyboard.get_first_entry_for_formation(formation)
        )
        frame_start = (
            storyboard_entry.frame_start
            if storyboard_entry
            else context.scene.frame_start
        )

        # create new markers for the points
        trajectories = [item.trajectory for item in imported_data.values()]
        first_points = [
            trajectory.first_point.as_vector()  # type: ignore
            for trajectory in trajectories
        ]
        markers = add_points_to_formation(formation, first_points)

        # create animation action for each point in the formation
        for trajectory, marker in zip(trajectories, markers):
            trajectory.simplify_in_place()
            if len(trajectory.points) <= 1:
                # does not need animation so we don't create the action
                continue

            action = ensure_action_exists_for_object(
                marker, name=f"Animation data for {marker.name}"
            )

            f_curves = []
            for i in range(3):
                f_curve = find_f_curve_for_data_path_and_index(action, "location", i)
                if f_curve is None:
                    f_curve = action.fcurves.new("location", index=i)
                else:
                    # We should clear the keyframes that fall within the
                    # range of our keyframes. Currently it's not needed because
                    # it's a freshly created marker so it can't have any
                    # keyframes that we don't know about.
                    pass
                f_curves.append(f_curve)

            t0 = trajectory.points[0].t
            insert = [
                partial(f_curve.keyframe_points.insert, options={"FAST"})
                for f_curve in f_curves
            ]
            for point in trajectory.points:
                frame = frame_start + int((point.t - t0) * fps)
                keyframes = (
                    insert[0](frame, point.x),
                    insert[1](frame, point.y),
                    insert[2](frame, point.z),
                )
                for keyframe in keyframes:
                    keyframe.interpolation = "LINEAR"

            # Commit the insertions that we've made in "fast" mode
            for f_curve in f_curves:
                f_curve.update()

        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


def parse_compressed_csv_zip(filename: str, context) -> Dict[str, ImportedData]:
    """Parse a .zip file containing Skybrush .csv files (one file per drone,
    each containing baked animation with timestamped positions and colors).

    Args:
        filename: the name of the .zip input file
        context: the Blender context

    Returns:
        dictionary mapping the imported object names to the corresponding
        timestamps, positions and colors

    Raises:
        RuntimeError: on parse errors
    """
    result: Dict[str, ImportedData] = {}

    with ZipFile(filename, "r") as zip_file:
        for filename in zip_file.namelist():
            name = Path(filename).stem
            if name in result:
                raise RuntimeError(f"Duplicate object name in input CSV files: {name}")

            data = ImportedData()
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
                        if row[0].lower().startswith("time_msec"):
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
