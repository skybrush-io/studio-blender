import bpy

from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
)
from bpy.types import Context, PropertyGroup
from operator import attrgetter
from typing import Optional

from sbstudio.plugin.constants import (
    DEFAULT_STORYBOARD_ENTRY_DURATION,
    DEFAULT_STORYBOARD_TRANSITION_DURATION,
)
from sbstudio.plugin.errors import StoryboardValidationError
from sbstudio.plugin.props import FormationProperty
from sbstudio.plugin.utils import with_context

from .mixins import ListMixin

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
        options=set(),
    )
    formation = FormationProperty(
        description=(
            "Formation to use in this storyboard entry. Leave empty to mark this "
            "interval in the show as a segment that should not be affected by "
            "formation constraints."
        ),
        update=_handle_formation_change,
        options=set(),
    )
    frame_start = IntProperty(
        name="Start Frame",
        description="Frame when this formation should start in the show",
        default=0,
        options=set(),
    )
    duration = IntProperty(
        name="Duration",
        description="Duration of this formation",
        default=0,
        options=set(),
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
        options=set(),
    )

    def contains_frame(self, frame: int) -> bool:
        """Returns whether the storyboard entry contains the given frame.

        Storyboard entries are closed from the left and open from the right;
        in other words, they always contain their start frames but they do not
        contain their end frames.
        """
        return 0 <= (frame - self.frame_start) < self.duration

    @property
    def frame_end(self) -> int:
        """Returns the index of the last frame that is covered by the storyboard."""
        return self.frame_start + self.duration


class Storyboard(PropertyGroup, ListMixin):
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

    @with_context
    def append_new_entry(
        self,
        name: str,
        frame_start: Optional[int] = None,
        duration: Optional[int] = None,
        *,
        select: bool = False,
        context: Optional[Context] = None,
    ) -> StoryboardEntry:
        """Appends a new entry to the end of the storyboard.

        Parameters:
            name: the name of the new entry
            frame_start: the start frame of the new entry; `None` chooses a
                sensible default
            duration: the duration of the new entry; `None` chooses a sensible
                default
            select: whether to select the newly added entry after it was created
        """
        fps = context.scene.render.fps
        if frame_start is None:
            frame_start = (
                self.frame_end + fps * DEFAULT_STORYBOARD_TRANSITION_DURATION
                if self.entries
                else context.scene.frame_start
            )

        if duration is None or duration <= 0:
            duration = fps * DEFAULT_STORYBOARD_ENTRY_DURATION

        entry = self.entries.add()
        entry.frame_start = frame_start
        entry.duration = duration
        entry.name = name

        if select:
            self.active_entry_index = len(self.entries) - 1

        return entry

    def contains_formation(self, formation) -> bool:
        """Returns whether the storyboard contains at least one entry referring
        to the given formation.
        """
        return any(entry.formation == formation for entry in self.entries)

    @property
    def first_entry(self) -> StoryboardEntry:
        """Returns the first entry of the storyboard or `None` if the storyboard
        is empty.
        """
        if self.entries:
            return self.entries[0]
        else:
            return None

    @property
    def first_formation(self):
        """Returns the first formation of the storyboard or `None` if the storyboard
        is empty.
        """
        entry = self.first_entry
        return entry.formation if entry else None

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

    def get_index_of_entry_containing_frame(self, frame: int) -> int:
        """Returns the index of the storyboard entry containing the given
        frame.

        Returns:
            the index of the storyboard entry containing the given frame, or
            -1 if the current frame does not belong to any of the entries
        """
        for index, entry in enumerate(self.entries):
            if entry.contains_frame(frame):
                return index
        return -1

    def get_index_of_entry_after_frame(self, frame: int) -> int:
        """Returns the index of the storyboard entry that comes after the given
        frame.

        Returns:
            the index of the storyboard entry containing the given frame, or
            -1 if the current frame is after the end of the storyboard
        """
        best_distance, closest = float("inf"), -1
        for index, entry in enumerate(self.entries):
            if entry.frame_start > frame:
                diff = entry.frame_start - frame
                if diff < best_distance:
                    best_distance = diff
                    closest = index

        return closest

    @property
    def last_entry(self) -> Optional[StoryboardEntry]:
        """Returns the last entry of the storyboard or `None` if the storyboard
        is empty.
        """
        if self.entries:
            return self.entries[len(self.entries) - 1]
        else:
            return None

    @property
    def last_formation(self):
        """Returns the last formation of the storyboard or `None` if the storyboard
        is empty.
        """
        entry = self.last_entry
        return entry.formation if entry else None

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

    def _on_active_entry_moving_down(self, this_entry, next_entry) -> bool:
        pad = next_entry.frame_start - this_entry.frame_end

        this_entry.frame_start, next_entry.frame_start = (
            this_entry.frame_start + next_entry.duration + pad,
            this_entry.frame_start,
        )

        return True

    def _on_active_entry_moving_up(self, this_entry, prev_entry) -> bool:
        pad = this_entry.frame_start - prev_entry.frame_end

        this_entry.frame_start, prev_entry.frame_start = (
            prev_entry.frame_start,
            prev_entry.frame_start + this_entry.duration + pad,
        )

        return True
