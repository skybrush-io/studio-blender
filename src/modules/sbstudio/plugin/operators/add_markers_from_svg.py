from numpy import array
from numpy.typing import NDArray
from pathlib import Path
from typing import Tuple

from bpy.path import ensure_ext
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from sbstudio.plugin.api import call_api_from_blender_operator

from .base import StaticMarkerCreationOperator, PointsAndColors

__all__ = ("AddMarkersFromSVGOperator",)

#############################################################################
# Helper functions for the exporter
#############################################################################


class AddMarkersFromSVGOperator(StaticMarkerCreationOperator, ImportHelper):
    """Adds markers to the currently selected formatio from sampling an SVG file
    with colored path objects. Operator calls the backend API to get the
    sampled positions and colors from the SVG file.
    """

    bl_idname = "skybrush.add_markers_from_svg"
    bl_label = "Import Skybrush SVG"
    bl_description = (
        "Creates a new formation whose points are sampled from an SVG file."
    )
    bl_options = {"REGISTER", "UNDO"}

    count = IntProperty(
        name="Count",
        description="Number of markers to be generated",
        default=100,
        min=1,
        soft_max=5000,
    )

    size = FloatProperty(
        name="Size",
        description="Maximum extent of the imported formation along the main axes",
        default=100,
        soft_min=0,
        soft_max=500,
        unit="LENGTH",
    )

    import_colors = BoolProperty(
        name="Import colors",
        description="Import colors from the SVG file into a light effect",
        default=False,
    )

    # List of file extensions that correspond to SVG files
    filter_glob = StringProperty(default="*.svg", options={"HIDDEN"})
    filename_ext = ".svg"

    def invoke(self, context, event):
        self.count = self._propose_marker_count(context)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def _create_points(self, context) -> PointsAndColors:
        filepath = ensure_ext(self.filepath, self.filename_ext)
        with call_api_from_blender_operator(self, "SVG formation") as api:
            points, colors = parse_svg(
                filepath, num_points=self.count, size=self.size, api=api
            )
        return PointsAndColors(points, colors)


def parse_svg(
    filename: str, *, num_points: int, size: float, api
) -> Tuple[NDArray[float], NDArray[float]]:
    """Parse an .svg file (containing a list of static positions and colors)
    using the backend API

    Args:
        filename: the name of the .svg input file
        num_points: the number of points to generate
        size: the maximum extent of the points along the main axes
        context: the Blender context

    Returns:
        the parsed list of positions and corresponding colors

    Raises:
        SkybrushStudioAPIError: on API parse errors
    """
    source = Path(filename).read_text()

    points, colors = api.create_formation_from_svg(
        source=source, num_points=num_points, size=size
    )

    # rotate from XY to ZY plane
    points = array([(0, p.y, p.x) for p in points], dtype=float)
    colors = array(
        [(c.r / 255, c.g / 255, c.b / 255, 1.0) for c in colors], dtype=float
    )

    return points, colors
