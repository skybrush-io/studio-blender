from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional

from bpy.types import Collection, Operator
from numpy import array
from numpy.typing import NDArray

from sbstudio.plugin.errors import StoryboardValidationError
from sbstudio.plugin.model.formation import add_points_to_formation
from sbstudio.plugin.selection import select_only


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


@dataclass
class PointsAndColors:
    points: NDArray[float]
    """The points to create in a static marker creation operation, in a NumPy
    array where each row is a point.
    """

    colors: Optional[NDArray[float]] = None
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

        # Add a light effect containing the colors of the markers if needed
        if colors is not None:
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
                light_effect.output = "INDEXED_BY_FORMATION"
                image = light_effect.create_color_image(
                    name="Image for light effect '{}'".format(formation.name),
                    width=1,
                    height=len(colors),
                )
                image.pixels.foreach_set(list(colors.flat))

        return {"FINISHED"}

    @abstractmethod
    def _create_points(self, context) -> PointsAndColors:
        """Creates the points where the markers should be placed."""
        raise NotImplementedError
