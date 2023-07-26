import bpy
import os

from abc import abstractmethod
from dataclasses import dataclass
from numpy import array, floating
from numpy.typing import NDArray
from typing import Any, Dict, Optional

from bpy.props import BoolProperty
from bpy.types import Collection, Operator
from bpy_extras.io_utils import ExportHelper

from sbstudio.model.file_formats import FileFormat
from sbstudio.plugin.errors import StoryboardValidationError
from sbstudio.plugin.model.formation import (
    add_points_to_formation,
    get_markers_from_formation,
)
from sbstudio.plugin.props.frame_range import FrameRangeProperty
from sbstudio.plugin.selection import select_only
from sbstudio.plugin.selection import Collections


class FormationOperator(Operator):
    """Operator mixin that allows an operator to be executed if we have a
    selected formation in the current scene.
    """

    @classmethod
    def poll(cls, context):
        return (
            context.scene.skybrush
            and context.scene.skybrush.formations
            and (
                getattr(cls, "works_with_no_selected_formation", False)
                or context.scene.skybrush.formations.selected
            )
        )

    def execute(self, context):
        return self.execute_on_formation(self.get_formation(context), context)

    def get_formation(self, context) -> Collection:
        return getattr(context.scene.skybrush.formations, "selected", None)

    @staticmethod
    def select_formation(formation, context) -> None:
        """Selects the given formation, both in the scene and in the formations
        panel.
        """
        select_only(formation)
        if context.scene.skybrush.formations:
            context.scene.skybrush.formations.selected = formation


class LightEffectOperator(Operator):
    """Operator mixin that allows an operator to be executed if we have a
    light effects object in the current scene.
    """

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush and context.scene.skybrush.light_effects

    def execute(self, context):
        light_effects = context.scene.skybrush.light_effects
        return self.execute_on_light_effect_collection(light_effects, context)


class StoryboardOperator(Operator):
    """Operator mixin that allows an operator to be executed if we have a
    storyboard in the current scene.
    """

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush and context.scene.skybrush.storyboard

    def execute(self, context):
        storyboard = context.scene.skybrush.storyboard

        validate = getattr(self.__class__, "only_with_valid_storyboard", False)

        if validate:
            try:
                entries = storyboard.validate_and_sort_entries()
            except StoryboardValidationError as ex:
                self.report({"ERROR_INVALID_INPUT"}, str(ex))
                return {"CANCELLED"}

            return self.execute_on_storyboard(storyboard, entries, context)
        else:
            return self.execute_on_storyboard(storyboard, context)


class StoryboardEntryOperator(Operator):
    """Operator mixin that allows an operator to be executed if we have a
    selected storyboard entry in the current scene.
    """

    @classmethod
    def poll(cls, context):
        return (
            context.scene.skybrush
            and context.scene.skybrush.storyboard
            and context.scene.skybrush.storyboard.active_entry
        )

    def execute(self, context):
        entry = context.scene.skybrush.storyboard.active_entry
        return self.execute_on_storyboard_entry(entry, context)


class ExportOperator(Operator, ExportHelper):
    """Operator mixin for operators that export the scene in some format using
    the Skybrush Studio API.
    """

    # whether to output all objects or only selected ones
    export_selected = BoolProperty(
        name="Export selected drones only",
        default=False,
        description=(
            "Export only the selected drones. "
            "Uncheck to export all drones, irrespectively of the selection."
        ),
    )

    # frame range
    frame_range = FrameRangeProperty(default="RENDER")

    def execute(self, context):
        from sbstudio.plugin.api import call_api_from_blender_operator
        from .utils import export_show_to_file_using_api

        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)

        if os.path.basename(filepath).lower() == self.filename_ext.lower():
            self.report({"ERROR_INVALID_INPUT"}, "Filename must not be empty")
            return {"CANCELLED"}

        settings = {
            "export_selected": self.export_selected,
            "frame_range": self.frame_range,
            **self.get_settings(),
        }

        try:
            with call_api_from_blender_operator(self, self.get_operator_name()) as api:
                export_show_to_file_using_api(
                    api, context, settings, filepath, self.get_format()
                )
        except Exception:
            return {"CANCELLED"}

        self.report({"INFO"}, "Export successful")
        return {"FINISHED"}

    def get_format(self) -> FileFormat:
        """Returns the file format that the operator uses. Must be overridden
        in subclasses.
        """
        raise NotImplementedError

    def get_operator_name(self) -> str:
        """Returns the name of the operator to be used in error messages when
        the operation fails.
        """
        return "exporter"

    def get_settings(self) -> Dict[str, Any]:
        """Returns operator-specific renderer settings that should be passed to
        the Skybrush Studio API.
        """
        return {}

    def invoke(self, context, event):
        if not hasattr(self, "filename_ext") or not self.filename_ext:
            raise RuntimeError("filename_ext not defined in exporter class")

        if not self.filepath:
            filepath = bpy.data.filepath or "Untitled"
            filepath, _ = os.path.splitext(filepath)
            self.filepath = f"{filepath}{self.filename_ext}"

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


@dataclass
class PointsAndColors:
    points: NDArray[floating]
    """The points to create in a static marker creation operation, in a NumPy
    array where each row is a point.
    """

    colors: Optional[NDArray[floating]] = None
    """Optional colors corresponding to the points in a marker creation
    operation, in a NumPy array where the i-th row is the color of the i-th
    point in RGBA space; color components must be specified in the range [0; 1].
    """


class StaticMarkerCreationOperator(FormationOperator):
    """Base class for operators that create a set of markers for a formation,
    optionally extended with a list of colors corresponding to the points.
    """

    def execute_on_formation(self, formation, context):
        # Construct the point set
        try:
            points_and_colors = self._create_points(context)
        except RuntimeError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        points = points_and_colors.points
        colors = points_and_colors.colors

        if len(points) < 1:
            self.report({"ERROR"}, "Formation would be empty, nothing was created")
            return {"CANCELLED"}

        # Align the center of the bounding box of the point set to the origin
        mins, maxs = points.min(axis=0), points.max(axis=0)
        points -= (maxs + mins) / 2

        # Move the origin of the point set to the 3D cursor
        points += array(context.scene.cursor.location, dtype=float)

        # Create the markers
        add_points_to_formation(formation, points.tolist())

        # Decide whether we should import the colors of the markers as well
        should_import_colors = (
            bool(getattr(self, "import_colors", True)) and colors is not None
        )

        # Add a light effect containing the colors of the markers if needed
        if should_import_colors:
            # try to figure out the start frame of this formation
            storyboard_entry = (
                context.scene.skybrush.storyboard.get_first_entry_for_formation(
                    formation
                )
            )
            frame_start = (
                storyboard_entry.frame_start
                if storyboard_entry
                else context.scene.frame_start
            )
            duration = storyboard_entry.duration if storyboard_entry else 1

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
                light_effect.output = "TEMPORAL"
                light_effect.output_y = "INDEXED_BY_FORMATION"
                light_effect.type = "IMAGE"
                image = light_effect.create_color_image(
                    name="Image for light effect '{}'".format(formation.name),
                    width=1,
                    height=len(colors),
                )
                image.pixels.foreach_set(list(colors.flat))
                image.pack()

        return {"FINISHED"}

    @abstractmethod
    def _create_points(self, context) -> PointsAndColors:
        """Creates the points where the markers should be placed."""
        raise NotImplementedError

    def _propose_marker_count(self, context) -> int:
        """Calculates how many markers we need to add to the currently selected
        formation in order to make it have exactly the same number of markers
        as the number of drones in the project.
        """
        drones = Collections.find_drones(create=False)
        num_drones = len(drones.objects) if drones else 0
        if num_drones > 0:
            num_existing_markers = len(
                get_markers_from_formation(context.scene.skybrush.formations.selected)
            )
        else:
            num_existing_markers = 0
        return max(0, num_drones - num_existing_markers)
