from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bpy.types import Constraint, CopyLocationConstraint, Object

from .identifiers import create_internal_id, is_internal_id

if TYPE_CHECKING:
    from sbstudio.plugin.model import StoryboardEntry


__all__ = (
    "create_transition_constraint_between",
    "find_transition_constraint_between",
    "get_id_for_formation_constraint",
    "is_transition_constraint",
    "set_constraint_name_from_storyboard_entry",
)


def get_id_for_formation_constraint(storyboard_entry: StoryboardEntry):
    """Returns a unique identifier for the given storyboard entry."""
    # Make sure to update is_transition_constraint() as well if you change the
    # format of the ID
    return create_internal_id(f"Entry {storyboard_entry.id}")


def create_transition_constraint_between(
    drone: Object, storyboard_entry: StoryboardEntry
) -> CopyLocationConstraint:
    """Creates a transition constraint between the given drone and an arbitrary
    entry in the storyboard.

    It is assumed that there is no such constraint between the drone and the
    storyboard entry yet.

    Returns:
        the constraint that was created
    """
    constraint = drone.constraints.new(type="COPY_LOCATION")
    constraint.name = get_id_for_formation_constraint(storyboard_entry)
    constraint.influence = 0

    return cast(CopyLocationConstraint, constraint)


def find_transition_constraint_between(
    drone: Object, storyboard_entry: StoryboardEntry
) -> CopyLocationConstraint | None:
    """Finds the Blender "copy location" constraint object that exists between
    the given drone and any of the points of the formation of the given
    storyboard entry; the purpose of this constraint is to keep the drone at
    the location of the point in the formation and to drive it towards / away
    from it during transitions.

    Returns:
        the constraint or `None` if no such constraint exists
    """
    expected_id = get_id_for_formation_constraint(storyboard_entry)

    for constraint in drone.constraints:
        if constraint.type == "COPY_LOCATION" and constraint.name == expected_id:
            return cast(CopyLocationConstraint, constraint)

    return None


def is_transition_constraint(constraint: Constraint) -> bool:
    """Returns whether the given constraint object is a transition constraint,
    judging from its name and type.
    """
    return (
        constraint
        and getattr(constraint, "type", None) == "COPY_LOCATION"
        and is_internal_id(constraint.name)
        and "[Entry " in constraint.name
    )


def set_constraint_name_from_storyboard_entry(
    constraint: Constraint, storyboard_entry: StoryboardEntry
) -> None:
    """Updates the name of the given constraint such that it refers to the given
    storyboard entry.
    """
    constraint.name = get_id_for_formation_constraint(storyboard_entry)
