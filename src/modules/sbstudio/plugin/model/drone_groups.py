from __future__ import annotations

from typing import Iterable

import bpy
from bpy.props import IntProperty
from bpy.types import Collection, Context, Object, PropertyGroup

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.utils import with_context

__all__ = ("DroneGroupsProperties", "get_drone_groups")


class DroneGroupsProperties(PropertyGroup):
    active_group_index: int = IntProperty(
        name="Selected index",
        description="Index of the drone group entry currently being edited",
    )
    """Index of the active entry (currently being edited) in the storyboard"""

    @property
    def active_group(self) -> Collection | None:
        """The active drone group currently selected for editing, or `None` if there is
        no such entry.
        """
        drone_groups = Collections.find_drone_groups(create=False)
        if not drone_groups:
            return None

        index = self.active_group_index
        if index is not None and index >= 0 and index < len(drone_groups.children):
            return drone_groups.children[index]
        else:
            return None

    @active_group.setter
    def active_group(self, group: Collection | None):
        if group is None:
            self.active_group_index = -1
            return

        drone_groups = Collections.find_drone_groups(create=False)
        if not drone_groups:
            return

        for i, existing_group in enumerate(drone_groups.children):
            if existing_group == group:
                self.active_group_index = i
                return
        else:
            self.active_group_index = -1

    def add_new_group(
        self, name: str = "New Drone Group", *, select: bool = False
    ) -> Collection:
        """Creates a new drone group and adds it to the list of drone groups."""
        drone_groups = Collections.find_drone_groups(create=True)

        new_group = bpy.data.collections.new(name)
        drone_groups.children.link(new_group)

        if select:
            self.active_group = new_group

        return new_group

    def extend_group(self, group: Collection, objects: Iterable[Object]) -> int:
        """Adds the given drones to the given drone group.

        Non-drone objects are ignored.

        Returns:
            the numbre of drones that were added to the group
        """
        drones = Collections.find_drones(create=False)
        if not drones:
            return 0

        drone_objects = drones.objects
        group_objects = group.objects
        added = 0

        for obj in objects:
            if obj.name in drone_objects and obj.name not in group_objects:
                group_objects.link(obj)
                added += 1

        return added

    def remove_group(self, group: Collection) -> None:
        """Removes the given drone group from the list of drone groups."""
        if self.active_group == group:
            self.active_group = None
        bpy.data.collections.remove(group)


@with_context
def get_drone_groups(*, context: Context | None = None) -> DroneGroupsProperties:
    """Helper function to retrieve the storyboard of the add-on from the
    given context object.
    """
    assert context is not None
    return context.scene.skybrush.drone_groups
