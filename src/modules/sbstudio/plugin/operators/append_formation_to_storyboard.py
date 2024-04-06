from math import ceil

from .base import FormationOperator

from sbstudio.plugin.api import get_api
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.model.formation import (
    get_world_coordinates_of_markers_from_formation,
)
from sbstudio.plugin.utils.evaluator import create_position_evaluator

__all__ = ("AppendFormationToStoryboardOperator",)


class AppendFormationToStoryboardOperator(FormationOperator):
    """Blender operator that appends the selected formation to the storyboard."""

    bl_idname = "skybrush.append_formation_to_storyboard"
    bl_label = "Append Selected Formation to Storyboard"
    bl_description = (
        "Appends the selected formation to the end of the show, planning the "
        "transition between the last formation and the new one"
    )

    @classmethod
    def poll(cls, context):
        if not FormationOperator.poll(context):
            return False

        formations = context.scene.skybrush.formations
        storyboard = getattr(context.scene.skybrush, "storyboard", None)
        if storyboard:
            return (
                not storyboard.entries
                or storyboard.entries[-1].formation != formations.selected
            )
        else:
            return False

    def execute_on_formation(self, formation, context):
        storyboard = getattr(context.scene.skybrush, "storyboard", None)
        if not storyboard or (
            storyboard.entries and storyboard.entries[-1].formation == formation
        ):
            return {"CANCELLED"}

        safety_check = getattr(context.scene.skybrush, "safety_check", None)
        settings = getattr(context.scene.skybrush, "settings", None)

        last_formation = storyboard.last_formation
        last_frame = storyboard.frame_end

        entry = storyboard.add_new_entry(
            name=formation.name, select=True, formation=formation
        )
        assert entry is not None

        fps = context.scene.render.fps

        # Set up safety check parameters
        safety_kwds = {
            "max_velocity_xy": (
                safety_check.velocity_xy_warning_threshold if safety_check else 8
            ),
            "max_velocity_z": (
                safety_check.velocity_z_warning_threshold if safety_check else 2
            ),
            "max_velocity_z_up": (
                safety_check.velocity_z_warning_threshold_up_or_none
                if safety_check
                else None
            ),
            "max_acceleration": settings.max_acceleration if settings else 4,
        }

        with create_position_evaluator() as get_positions_of:
            if last_formation is not None:
                source = get_world_coordinates_of_markers_from_formation(
                    last_formation, frame=last_frame
                )
                source = [tuple(coord) for coord in source]
            else:
                drones = Collections.find_drones().objects
                source = get_positions_of(drones, frame=last_frame)

            target = get_world_coordinates_of_markers_from_formation(
                formation, frame=entry.frame_start
            )
            target = [tuple(coord) for coord in target]
        try:
            plan = get_api().plan_transition(source, target, **safety_kwds)
        except Exception:
            raise
            self.report(
                {"ERROR"},
                "Error while invoking transition planner on the Skybrush Studio server",
            )
            return {"CANCELLED"}

        # To get nicer-looking frame counts, we round the end of the
        # transition up to the next whole second. We need to take into account
        # whether the scene starts from frame 1 or 0 or anything else
        # stored in storyboard.frame_start, though.
        new_start = ceil(
            last_frame + (plan.total_duration if plan.durations else 10) * fps
        )
        diff = ceil((new_start - storyboard.frame_start) / fps) * fps
        entry.frame_start = storyboard.frame_start + diff

        return {"FINISHED"}
