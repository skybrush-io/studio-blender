import bpy

from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
)
from bpy.types import PropertyGroup
from operator import attrgetter
from typing import Optional

from sbstudio.plugin.errors import StoryboardValidationError
from sbstudio.plugin.props import FormationProperty


__all__ = ("StoryboardEntry", "Storyboard")


def _handle_formation_change(operator, context):
    if not operator.is_name_customized:
        operator.name = operator.formation.name if operator.formation else ""


class StoryboardEntry(PropertyGroup):
    """Blender property group representing a single entry in the storyboard
    of the drone show.
    """

    is_name_customized = BoolProperty(
        name="Custom Name",
        description="Keeps the name of the storyboard entry when the associated formation changes",
        default=False,
    )
    formation = FormationProperty(
        description=(
            "Formation to use in this storyboard entry. Leave empty to mark this "
            "interval in the show as a segment that should not be affected by "
            "formation constraints."
        ),
        update=_handle_formation_change,
    )
    frame_start = IntProperty(
        name="Start Frame",
        description="Frame when this formation should start in the show",
        default=0,
    )
    duration = IntProperty(
        name="Duration",
        description="Duration of this formation",
        default=0,
    )
    transition_type = EnumProperty(
        items=[
            ("MANUAL", "Manual", "", 1),
            ("AUTO", "Auto", "", 2),
        ],
        name="Transition",
        description="Type of transition between the previous formation and this one. "
        "Manual transitions map the nth vertex of the initial formation to the nth "
        "vertex of the target formation; auto-matched transitions find an "
        "optimal mapping between vertices of the initial and the target formation.",
        default="AUTO",
    )

    @property
    def frame_end(self) -> int:
        """Returns the index of the last frame that is covered by the storyboard."""
        return self.frame_start + self.duration


class Storyboard(PropertyGroup):
    """Blender property group representing the entire storyboard of the
    drone show.
    """

    #: The entries in this storyboard
    entries = CollectionProperty(type=StoryboardEntry)

    #: Index of the active entry (currently being edited) in the storyboard
    active_entry_index = IntProperty(
        name="Selected index",
        description="Index of the storyboard entry currently being edited",
    )

    @property
    def active_entry(self) -> Optional[StoryboardEntry]:
        """The active storyboard entry currently selected for editing, or
        `None` if there is no such entry.
        """
        index = self.active_entry_index
        if index is not None and index >= 0 and index < len(self.entries):
            return self.entries[index]
        else:
            return None

    @property
    def frame_end(self) -> int:
        """Returns the index of the last frame that is covered by the storyboard."""
        return (
            max(entry.frame_end for entry in self.entries)
            if self.entries
            else self.frame_start
        )

    @property
    def frame_start(self) -> int:
        """Returns the index of the first frame that is covered by the storyboard."""
        return (
            min(entry.frame_start for entry in self.entries)
            if self.entries
            else bpy.context.scene.frame_start
        )

    def move_active_entry_down(self) -> None:
        """Moves the active entry one slot down in the storyboard and adjusts the
        active entry index as needed.
        """
        index = self.active_entry_index
        num_entries = len(self.entries)
        if index < num_entries - 1:
            this_entry = self.entries[index]
            next_entry = self.entries[index + 1]
            pad = next_entry.frame_start - this_entry.frame_end

            this_entry.frame_start, next_entry.frame_start = (
                this_entry.frame_start + next_entry.duration + pad,
                this_entry.frame_start,
            )

            self.entries.move(index, index + 1)
            self.active_entry_index = index + 1

    def move_active_entry_up(self) -> None:
        """Moves the active entry one slot up in the storyboard and adjusts the
        active entry index as needed.
        """
        index = self.active_entry_index
        if index > 0:
            prev_entry = self.entries[index - 1]
            this_entry = self.entries[index]
            pad = this_entry.frame_start - prev_entry.frame_end

            this_entry.frame_start, prev_entry.frame_start = (
                prev_entry.frame_start,
                prev_entry.frame_start + this_entry.duration + pad,
            )

            self.entries.move(index, index - 1)
            self.active_entry_index = index - 1

    def remove_active_entry(self) -> None:
        """Removes the active entry from the storyboard and adjusts the active
        entry index as needed.
        """
        index = self.active_entry_index
        self.entries.remove(index)
        self.active_entry_index = min(max(0, index), len(self.entries))

    def validate_and_sort_entries(self) -> None:
        """Validates the entries in the storyboard and sorts them by start time,
        keeping the active entry index point to the same entry as before.

        Returns:
            the list of entries in the storyboard, sorted by start time

        Raises:
            StoryboardValidationError: if the storyboard contains overlapping
                formations
        """
        entries = list(self.entries)
        entries.sort(key=attrgetter("frame_start"))

        for index, (entry, next_entry) in enumerate(zip(entries, entries[1:])):
            if entry.frame_end > next_entry.frame_start:
                raise StoryboardValidationError(
                    f"Storyboard entry {entry.name!r} at index {index + 1} "
                    f"overlaps with next entry {next_entry.name!r}"
                )

        # Currently we don't support the same formation appearing multiple times
        # in the storyboard. This should be improved later. TODO(ntamas)
        formation_set = set(entry.formation for entry in entries)
        if len(formation_set) < len(entries):
            raise StoryboardValidationError(
                "Each formation may appear only once in the storyboard"
            )

        # TODO(ntamas): implement sorting. Unfortunately the API of the collection
        # is so limited that we would need to implement insertion sort here
        # ourselves
        """
        if entries != list(self.entries):
            active_entry = self.active_entry
            new_active_index = entries.index(active_entry) if active_entry else 0

            # TODO(ntamas): sort here

            self.active_entry_index = new_active_index
        """

        return entries
