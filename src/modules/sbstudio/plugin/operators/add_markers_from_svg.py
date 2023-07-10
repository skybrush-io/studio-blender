import logging

from dataclasses import dataclass
from itertools import chain
from typing import List, Tuple

from bpy.path import ensure_ext
from bpy.props import FloatProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from sbstudio.api.errors import SkybrushStudioAPIError
from sbstudio.model.color import Color3D
from sbstudio.model.point import Point3D
from sbstudio.plugin.api import get_api
from sbstudio.plugin.model.formation import add_points_to_formation
from sbstudio.plugin.selection import Collections

from .base import FormationOperator

__all__ = ("AddMarkersFromSVGOperator",)

log = logging.getLogger(__name__)

#############################################################################
# Helper functions for the exporter
#############################################################################


@dataclass
class ImportedData:
    position: Point3D
    color: Color3D


class AddMarkersFromSVGOperator(FormationOperator, ImportHelper):
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

    # List of file extensions that correspond to SVG files
    filter_glob = StringProperty(default="*.svg", options={"HIDDEN"})
    filename_ext = ".svg"

    def execute_on_formation(self, formation, context):
        filepath = ensure_ext(self.filepath, self.filename_ext)

        # get positions and colors from an .svg file
        try:
            positions, colors = parse_svg(
                filepath, n=self.count, size=self.size, context=context
            )
        except RuntimeError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        # try to figure out the start frame of this formation
        storyboard_entry = (
            context.scene.skybrush.storyboard.get_first_entry_for_formation(formation)
        )
        frame_start = (
            storyboard_entry.frame_start
            if storyboard_entry
            else context.scene.frame_start
        )
        duration = storyboard_entry.duration if storyboard_entry else 1

        # create new markers for the points
        points = [point.as_vector() for point in positions]
        if not points:
            self.report({"ERROR"}, "Formation would be empty, nothing was created")
        else:
            add_points_to_formation(formation, points)

        # add a light effect from the imported colors
        light_effects = context.scene.skybrush.light_effects
        if light_effects:
            light_effects.append_new_entry(
                name=formation.name,
                frame_start=frame_start,
                duration=duration,
                select=True,
            )
            light_effect = light_effects.active_entry
            light_effect.output = "INDEXED_BY_FORMATION"
            image = light_effect.create_color_image(
                name="Image for light effect '{}'".format(formation.name),
                width=1,
                height=len(colors),
            )
            image.pixels.foreach_set(
                list(chain(*[list(color.as_vector()) for color in colors]))
            )

        return {"FINISHED"}

    def invoke(self, context, event):
        drones = Collections.find_drones(create=False)
        if drones:
            self.count = len(drones.objects)

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


def parse_svg(
    filename: str, n: int, size: float, context
) -> Tuple[List[Point3D], List[Color3D]]:
    """Parse an .svg file (containing a list of static positions and colors)
    using the backend API

    Args:
        filename: the name of the .svg input file
        n: the number of points to generate
        size: the maximum extent of the points along the main axes
        context: the Blender context

    Returns:
        the parsed list of positions and corresponding colors

    Raises:
        SkybrushStudioAPIError: on API parse errors

    """
    with open(filename, "r") as svg_file:
        source = svg_file.read()

        try:
            points, colors = get_api().create_formation_from_svg(
                source=source, n=n, size=size
            )
        except Exception as ex:
            if not isinstance(ex, SkybrushStudioAPIError):
                raise SkybrushStudioAPIError from ex
            else:
                raise

    # rotate from XY to ZY plane and shift to cursor position
    center = context.scene.cursor.location
    points = [Point3D(center.x, p.y + center.y, p.x + center.z) for p in points]

    return points, colors
