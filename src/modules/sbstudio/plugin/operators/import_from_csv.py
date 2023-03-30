import csv
import logging

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
from zipfile import ZipFile

from sbstudio.model.color import Color4D
from sbstudio.model.point import Point4D
from sbstudio.model.light_program import LightProgram
from sbstudio.model.trajectory import Trajectory
from sbstudio.plugin.actions import ensure_action_exists_for_object
from sbstudio.plugin.model.formation import get_markers_from_formation

from bpy.path import ensure_ext
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from sbstudio.plugin.model.formation import create_formation

__all__ = ("SkybrushCSVImportOperator",)

log = logging.getLogger(__name__)

#############################################################################
# Helper functions for the exporter
#############################################################################


@dataclass
class ImportedData:
    timestamps: List[float] = field(default_factory=list)
    trajectory: Trajectory = field(default_factory=Trajectory)
    light_program: LightProgram = field(default_factory=LightProgram)


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
            imported_data = parse_compressed_csv_zip(filepath, context)
        except RuntimeError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        # TODO(ntamas): make this configurable!
        start_frame = 1
        fps = context.scene.render.fps

        # create a static formation from the first points. Colors are not
        # handled yet.
        trajectories = [item.trajectory for item in imported_data.values()]
        first_points = [
            trajectory.first_point.as_vector()  # type: ignore
            for trajectory in trajectories
        ]
        formation = create_formation(self.formation_name, first_points)

        # create animation action for each point in the formation
        markers = get_markers_from_formation(formation)
        for trajectory, marker in zip(trajectories, markers):
            trajectory.simplify_in_place()

            action = ensure_action_exists_for_object(
                marker, name=f"Animation data for {marker.name}"
            )
            f_curves = [action.fcurves.new("location", index=i) for i in range(3)]

            t0 = trajectory.points[0].t
            insert = [f_curve.keyframe_points.insert for f_curve in f_curves]
            for point in trajectory.points:
                frame = start_frame + int((point.t - t0) * fps)
                insert[0](frame, point.x)
                insert[1](frame, point.y)
                insert[2](frame, point.z)

        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


def parse_compressed_csv_zip(filename: str, context) -> Dict[str, ImportedData]:
    """Parse a .zip file containing Skybrush .csv files.

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

            timestamps = data.timestamps
            trajectory = data.trajectory
            light_program = data.light_program

            with zip_file.open(filename, "r") as csv_file:
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
                            "Invalid content in input CSV file {filename!r}, row {row}"
                        )

                    # store position and color entry
                    timestamps.append(t)
                    trajectory.append(Point4D(t, x, y, z))
                    light_program.append(Color4D(t, r, g, b))

            # store the result only if there is at least one point, otherwise
            # there's nothing we can construct
            if timestamps:
                result[name] = data

    return result
