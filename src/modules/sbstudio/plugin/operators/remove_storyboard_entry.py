from __future__ import annotations

from typing import TYPE_CHECKING

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.model.storyboard import get_storyboard
from sbstudio.plugin.utils.transition import find_transition_constraint_between

from .base import StoryboardOperator

if TYPE_CHECKING:
    from bpy.types import Context

    from sbstudio.plugin.model.storyboard import Storyboard, StoryboardEntry

__all__ = ("RemoveStoryboardEntryOperator",)


class RemoveStoryboardEntryOperator(StoryboardOperator):
    """Blender operator that removes the selected storyboard entry."""

    bl_idname = "skybrush.remove_storyboard_entry"
    bl_label = "Remove Selected Storyboard Entry"
    bl_description = "Remove the selected entry from the storyboard"

    @classmethod
    def poll(cls, context: Context):
        return (
            StoryboardOperator.poll(context)
            and get_storyboard(context=context).active_entry is not None
        )

    def execute_on_storyboard(self, storyboard: Storyboard, context: Context):
        remove_constraints_for_storyboard_entry(storyboard.active_entry)
        storyboard.remove_active_entry()
        return {"FINISHED"}


def remove_constraints_for_storyboard_entry(entry: StoryboardEntry):
    if not entry:
        return

    drones = Collections.find_drones(create=False)
    if not drones:
        return

    for drone in drones.objects:
        constraint = find_transition_constraint_between(drone, entry)
        if constraint:
            drone.constraints.remove(constraint)
