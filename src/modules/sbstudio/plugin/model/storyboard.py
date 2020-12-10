import bpy

from bpy.props import (
    BoolProperty,
    CollectionProperty,
    IntProperty,
    PointerProperty,
)
from bpy.types import Collection, PropertyGroup
from typing import Optional

from .formation import is_formation


__all__ = ("StoryboardEntry", "Storyboard")


def _is_formation(self, object):
    return is_formation(object)


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
    formation = PointerProperty(
        name="Formation",
        description=(
            "Formation to use in this storyboard entry. Leave empty to mark this "
            "interval in the show as a segment that should not be affected by "
            "formation constraints."
        ),
        type=Collection,
        poll=_is_formation,
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

    def remove_active_entry(self) -> None:
        """Removes the active entry from the storyboard and adjusts the active
        entry index as needed.
        """
        index = self.active_entry_index
        self.entries.remove(index)
        self.active_entry_index = min(max(0, index), len(self.entries))
