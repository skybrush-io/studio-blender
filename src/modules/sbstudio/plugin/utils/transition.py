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


def get_bezier_inverse_smoothstep(
    x: float, length: float, *, iterations: int = 20
) -> float:
    """Returns the (approximated) inverse smoothstep function of the standard
    cubic Bezier interpolation used by Blender as the Easing function (3u^2-2u^3).

    The approximation is used by a simple binary search.

    Args:
        x: the partial distance of the transition at which we query
        length: the total length of the transition

    Returns:
        the inverse smoothstep function of the cubic Bezier curve
    """
    r = x / length

    lo, hi = 0.0, 1.0

    for _ in range(iterations):
        mid = (lo + hi) / 2
        s = 3 * mid * mid - 2 * mid * mid * mid

        if s < r:
            lo = mid
        else:
            hi = mid

    return (lo + hi) / 2


def get_time_of_partial_bezier_transition(x, length: float, speed: float) -> float:
    """Returns the time needed to travel only part of a transition, assuming
    standard cubic Bezier interpolation of the transition.

    Args:
        x: the partial distance at which we query the time when it is reached
        length: the total length of the transition
        speed: the averate speed of the transition

    Returns:
        the time needed to reach the given point as part of the transition
    """
    if x < 0 or x > length or speed <= 0:
        raise ValueError("Invalid input parameters")

    return (length / speed) * get_bezier_inverse_smoothstep(x, length)


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
