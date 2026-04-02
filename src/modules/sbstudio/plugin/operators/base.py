from __future__ import annotations

import logging
import os
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty
from bpy.types import Collection, Context, FCurve, Object, Operator
from bpy_extras.io_utils import ExportHelper
from numpy import array, floating
from numpy.typing import NDArray

from sbstudio.model.file_formats import FileFormat
from sbstudio.model.light_program import LightProgram
from sbstudio.model.point import Point3D
from sbstudio.model.trajectory import Trajectory
from sbstudio.plugin.actions import (
    ensure_f_curve_exists_for_data_path_and_index,
)
from sbstudio.plugin.errors import StoryboardValidationError
from sbstudio.plugin.model.formation import (
    add_points_to_formation,
    get_markers_from_formation,
)
from sbstudio.plugin.model.storyboard import get_storyboard
from sbstudio.plugin.props.frame_range import FrameRangeProperty
from sbstudio.plugin.selection import Collections, select_only

log = logging.getLogger(__name__)


class FormationOperator(Operator):
    """Operator mixin that allows an operator to be executed if we have a
    selected formation in the current scene.
    """

    @classmethod
    def poll(cls, context: Context):
        return (
            context.scene.skybrush
            and context.scene.skybrush.formations
            and (
                getattr(cls, "works_with_no_selected_formation", False)
                or context.scene.skybrush.formations.selected
            )
        )

    def execute(self, context: Context):
        return self.execute_on_formation(self.get_formation(context), context)

    def get_formation(self, context: Context) -> Collection:
        return getattr(context.scene.skybrush.formations, "selected", None)

    @staticmethod
    def select_formation(formation: Object, context: Context) -> None:
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
    def poll(cls, context: Context):
        return context.scene.skybrush and context.scene.skybrush.light_effects

    def execute(self, context: Context):
        light_effects = context.scene.skybrush.light_effects
        return self.execute_on_light_effect_collection(light_effects, context)


class StoryboardOperator(Operator):
    """Operator mixin that allows an operator to be executed if we have a
    storyboard in the current scene.
    """

    @classmethod
    def poll(cls, context: Context):
        return context.scene.skybrush and context.scene.skybrush.storyboard

    def execute(self, context: Context):
        storyboard = get_storyboard(context=context)

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
    def poll(cls, context: Context):
        return (
            context.scene.skybrush
            and context.scene.skybrush.storyboard
            and context.scene.skybrush.storyboard.active_entry
        )

    def execute(self, context: Context):
        entry = get_storyboard(context=context).active_entry
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

    # whether to redraw the scene during export
    redraw = EnumProperty(
        name="Redraw frames",
        items=[
            (
                "AUTO",
                "Auto",
                "Redraw the scene only if necessary for the light effects to work correctly",
            ),
            (
                "ALWAYS",
                "Always",
                "Redraw the scene even if it would not be needed for the light effects",
            ),
            (
                "NEVER",
                "Never",
                "Do not redraw the scene even if it would be needed for the light effects",
            ),
        ],
        default="AUTO",
        description="Whether to redraw the scene during export after every frame",
    )

    def execute(self, context: Context):
        from sbstudio.plugin.api import call_api_from_blender_operator

        from .utils import export_show_to_file_using_api

        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)

        if os.path.basename(filepath).lower() == self.filename_ext.lower():
            self.report({"ERROR_INVALID_INPUT"}, "Filename must not be empty")
            return {"CANCELLED"}

        settings = {
            "export_selected": self.export_selected,
            "frame_range": self.frame_range,
            "redraw": self._get_redraw_setting(),
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

    def get_settings(self) -> dict[str, Any]:
        """Returns operator-specific renderer settings that should be passed to
        the Skybrush Studio API.
        """
        return {}

    def invoke(self, context: Context, event):
        if not hasattr(self, "filename_ext") or not self.filename_ext:
            raise RuntimeError("filename_ext not defined in exporter class")

        if not self.filepath:
            filepath = bpy.data.filepath or "Untitled"
            filepath, _ = os.path.splitext(filepath)
            self.filepath = f"{filepath}{self.filename_ext}"

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def _get_redraw_setting(self) -> Optional[bool]:
        """Returns the redraw setting for the operator. This is used to
        determine whether to redraw the scene during export.
        """
        if self.redraw == "AUTO":
            return None
        elif self.redraw == "ALWAYS":
            return True
        else:
            return False


@dataclass
class TrajectoryAndLightProgram:
    timestamps: list[float] = field(default_factory=list)
    """Timestamps corresponding to ??? TODO ???"""

    trajectory: Trajectory = field(default_factory=Trajectory)
    """The trajectory to create in a dynamic marker creation operator."""

    light_program: LightProgram = field(default_factory=LightProgram)
    """Optional light program associated with the trajectory."""


class DynamicMarkerCreationOperator(FormationOperator):
    """Base class for operators that create a set of dynamic markers for a
    formation, with light animation corresponding to the formation.
    """

    def execute_on_formation(self, formation: Object, context: Context):
        # Construct the trajectory and light program to set
        try:
            trajectories_and_lights = self._create_trajectories(context)
        except RuntimeError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        # determine FPS of scene
        fps = context.scene.render.fps

        # try to figure out the start frame of this formation
        storyboard_entry = get_storyboard(
            context=context
        ).get_first_entry_for_formation(formation)
        frame_start = (
            storyboard_entry.frame_start
            if storyboard_entry
            else context.scene.frame_start
        )

        # create new markers for the points around cursor location
        center = Point3D(*context.scene.cursor.location)
        trajectories = [
            item.trajectory.shift_in_place(center)
            for item in trajectories_and_lights.values()
        ]
        first_points = [
            trajectory.first_point.as_vector()  # type: ignore
            for trajectory in trajectories
        ]
        markers = add_points_to_formation(formation, first_points)

        # update storyboard duration based on animation data
        if self.update_duration and storyboard_entry:
            duration = (
                int(max(trajectory.duration for trajectory in trajectories) * fps) + 1
            )
            storyboard_entry.duration = duration

        # create animation action for each point in the formation
        log.info("Creating trajectories...")
        for trajectory, marker in zip(trajectories, markers):
            trajectory.simplify_in_place()
            if len(trajectory.points) <= 1:
                # does not need animation so we don't create the action
                continue

            f_curves: list[FCurve] = []
            for i in range(3):
                f_curve = ensure_f_curve_exists_for_data_path_and_index(
                    marker, data_path="location", index=i
                )
                f_curves.append(f_curve)

            # add keypoints to f-curves in low level mode
            t0 = trajectory.points[0].t
            frames = [frame_start + int((p.t - t0) * fps) for p in trajectory.points]
            values_x = [p.x for p in trajectory.points]
            values_y = [p.y for p in trajectory.points]
            values_z = [p.z for p in trajectory.points]
            for f_curve, values in zip(f_curves, [values_x, values_y, values_z]):
                f_curve.keyframe_points.add(len(frames))
                for i, (frame, value) in enumerate(zip(frames, values)):
                    kp = f_curve.keyframe_points[i]
                    kp.co = (frame, value)
                    kp.interpolation = "LINEAR"
                    kp.handle_left_type = "AUTO_CLAMPED"
                    kp.handle_right_type = "AUTO_CLAMPED"

            # Commit the insertions that we've made in low level mode
            for f_curve in f_curves:
                f_curve.update()

        # store light program as a light effect with color image
        log.info("Creating light effects...")
        light_effects = context.scene.skybrush.light_effects
        light_programs = [
            item.light_program for item in trajectories_and_lights.values()
        ]
        if light_effects and light_programs:
            duration = (
                int(
                    (light_programs[0].colors[-1].t - light_programs[0].colors[0].t)
                    * fps
                )
                + 1
            )
            light_effects.append_new_entry(
                name=formation.name,
                frame_start=frame_start,
                duration=duration,
                select=True,
            )
            light_effect = light_effects.active_entry
            assert light_effect is not None

            light_effect.type = "IMAGE"
            light_effect.output = "TEMPORAL"
            light_effect.output_y = "INDEXED_BY_FORMATION"
            image = light_effect.create_color_image(
                name="Image for light effect '{}'".format(formation.name),
                width=duration,
                height=len(light_programs),
            )
            pixels = []
            for light_program in light_programs:
                color = light_program.colors[0]
                t0 = color.t
                j_last = 0
                for next_color in light_program.colors[1:]:
                    j_next = int((next_color.t - t0) * fps)
                    pixels.extend(list(color.as_vector()) * (j_next - j_last))
                    j_last = j_next
                    color = next_color
                pixels.extend(list(color.as_vector()))
            image.pixels.foreach_set(pixels)
            image.pack()

        if not trajectories_and_lights:
            self.report(
                {"WARNING"}, "No trajectories or light programs were found in the input"
            )

        return {"FINISHED"}

    @abstractmethod
    def _create_trajectories(
        self, context: Context
    ) -> dict[str, TrajectoryAndLightProgram]:
        """Creates the trajectories and light programs where the markers should be placed."""
        raise NotImplementedError


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

    def execute_on_formation(self, formation: Object, context: Context):
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
            storyboard_entry = get_storyboard(
                context=context
            ).get_first_entry_for_formation(formation)
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
                assert light_effect is not None

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
    def _create_points(self, context: Context) -> PointsAndColors:
        """Creates the points where the markers should be placed."""
        raise NotImplementedError

    def _propose_marker_count(self, context: Context) -> int:
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


class MigrationOperator(Operator):
    """Operator mixin for migrations/upgrades for files created in earlier
    versions of the Skybrush Studio for Blender plugin."""

    version_from = IntProperty(name="Input format version", options={"HIDDEN"})
    version_to = IntProperty(name="Output format version", options={"HIDDEN"})

    @classmethod
    def poll(cls, context: Context):
        return context.scene.skybrush

    def execute(self, context: Context):
        if context.scene.skybrush.version < self.version_from:
            raise RuntimeError(
                f"Input format version should be {self.version_from}, "
                f"not {context.scene.skybrush.version}"
            )
        elif context.scene.skybrush.version == self.version_from:
            retval = (
                self.execute_migration(context)
                if self.needs_migration()
                else {"FINISHED"}
            )
            if retval == {"FINISHED"}:
                context.scene.skybrush.version = self.version_to

            return retval

        return {"FINISHED"}

    def invoke(self, context: Context, event):
        self.initialize_migration()

        if context.scene.skybrush.version >= self.version_to:
            return {"CANCELLED"}

        if self.needs_migration():
            return context.window_manager.invoke_confirm(
                self, event, title=self.bl_label, message=self.bl_description
            )
        else:
            return self.execute(context)

    def execute_migration(self, context: Context):
        """Executes the migration/upgrade on the current Blender content."""
        raise NotImplementedError

    def initialize_migration(self) -> None:
        """Initializes the operator by setting up the from/to versions."""
        raise NotImplementedError

    def needs_migration(self) -> bool:
        """Returns whether the current Blender content needs migration.

        Note that return value is checked based on actual content,
        irrespective of the current plugin version."""
        raise NotImplementedError
