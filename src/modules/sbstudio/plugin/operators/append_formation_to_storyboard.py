from math import ceil

from .base import FormationOperator

from sbstudio.plugin.api import get_api
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.model.formation import get_all_markers_from_formation
from sbstudio.plugin.utils.evaluator import create_position_evaluator

__all__ = ("AppendFormationToStoryboardOperator",)


class AppendFormationToStoryboardOperator(FormationOperator):
    """Blender operator that appends the selected formation to the storyboard."""

    bl_idname = "skybrush.append_formation_to_storyboard"
    bl_label = "Append Selected Formation to Storyboard"
    bl_description = "Appends the selected formation to the end of the show, planning the transition between the last formation and the new one."

    @classmethod
    def poll(cls, context):
        if not FormationOperator.poll(context):
            return False

        formations = context.scene.skybrush.formations
        storyboard = getattr(context.scene.skybrush, "storyboard", None)
        if storyboard:
            return not storyboard.contains_formation(formations.selected)
        else:
            return False

    def execute_on_formation(self, formation, context):
        storyboard = getattr(context.scene.skybrush, "storyboard", None)
        if not storyboard or storyboard.contains_formation(formation):
            return {"CANCELLED"}

        safety_check = getattr(context.scene.skybrush, "safety_check", None)
        settings = getattr(context.scene.skybrush, "settings", None)

        last_formation = storyboard.last_formation
        last_frame = storyboard.frame_end

        entry = storyboard.append_new_entry(name=formation.name, select=True)
        entry.formation = formation

        fps = context.scene.render.fps

        with create_position_evaluator() as get_positions_of:
            if last_formation is not None:
                markers = get_all_markers_from_formation(last_formation)
                source = get_positions_of(markers, frame=last_frame)
            else:
                drones = Collections.find_drones().objects
                source = get_positions_of(drones, frame=last_frame)

            # TODO(ntamas): this works only if the target formation is
            # stationary
            markers = get_all_markers_from_formation(formation)
            target = get_positions_of(markers, frame=entry.frame_start)

            transition_duration = get_api().plan_transition(
                source,
                target,
                max_velocity_xy=safety_check.velocity_xy_warning_threshold
                if safety_check
                else 8,
                max_velocity_z=safety_check.velocity_z_warning_threshold
                if safety_check
                else 2,
                max_acceleration=settings.max_acceleration if settings else 4,
            )

            # To get nicer-looking frame counts, we round the end of the
            # transition up to the next whole second
            entry.frame_start = ceil(last_frame / fps + transition_duration) * fps

        return {"FINISHED"}
