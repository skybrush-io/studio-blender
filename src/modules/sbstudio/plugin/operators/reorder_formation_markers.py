from random import shuffle
from typing import List

import bpy

from bpy.props import EnumProperty

from sbstudio.plugin.utils.collections import sort_collection
from sbstudio.plugin.utils.evaluator import create_position_evaluator

from .base import FormationOperator

__all__ = ("ReorderFormationMarkersOperator",)


class ReorderFormationMarkersOperator(FormationOperator):
    """Re-orders individual markers within a formation."""

    bl_idname = "skybrush.reorder_formation_markers"
    bl_label = "Reorder Formation Markers"
    bl_description = "Re-orders individual markers within a formation"
    # bl_options = {}  # Don't add "UNDO" here, we handle that manually

    type = EnumProperty(
        items=[
            ("SHUFFLE", "Shuffle", "", 1),
            ("REVERSE", "Reverse", "", 2),
            ("X", "Sort by X coordinate", "", 3),
            ("Y", "Sort by Y coordinate", "", 4),
            ("Z", "Sort by Z coordinate", "", 5),
            ("EVERY_2", "Every 2nd", "", 6),
            ("EVERY_3", "Every 3rd", "", 7),
            ("EVERY_4", "Every 4th", "", 8),
        ],
        name="Type",
        description="Reordering to perform on the formation",
        default="SHUFFLE",
    )

    def execute_on_formation(self, formation, context):
        # TODO(ntamas): currently this works only for formations that consist
        # of empties. Formations based on vertex groups and formations that
        # consist of a mixture of empties _and_ vertex groups do not work.
        # We may add (limited) support for these in the future.

        if len(formation.children) > 0:
            self.report({"ERROR"}, "Formation must not contain sub-collections")
            return {"CANCELLED"}

        markers = formation.objects
        func = getattr(self, f"_execute_on_formation_{self.type}", None)
        if callable(func):
            index_vector: List[int] = func(markers)
            print(repr(index_vector))
            reversed_mapping = dict(
                (markers[marker_index], slot_index)
                for slot_index, marker_index in enumerate(index_vector)
            )
            bpy.ops.ed.undo_push()
            sort_collection(markers, reversed_mapping.__getitem__)
            self.report({"INFO"}, "Formation markers reordered")
            return {"FINISHED"}
        else:
            self.report({"ERROR"}, f"{self.type} method not implemented yet")
            return {"CANCELLED"}

    def _execute_on_formation_SHUFFLE(self, markers) -> List[int]:
        mapping = list(range(len(markers)))
        shuffle(mapping)
        return mapping

    def _execute_on_formation_REVERSE(self, markers) -> List[int]:
        return list(reversed(range(len(markers))))

    def _execute_on_formation_X(self, markers) -> List[int]:
        return self._sort_by_axis(markers, axis=0)

    def _execute_on_formation_Y(self, markers) -> List[int]:
        return self._sort_by_axis(markers, axis=1)

    def _execute_on_formation_Z(self, markers) -> List[int]:
        return self._sort_by_axis(markers, axis=2)

    def _execute_on_formation_EVERY_2(self, markers) -> List[int]:
        return self._sweep(markers, step=2)

    def _execute_on_formation_EVERY_3(self, markers) -> List[int]:
        return self._sweep(markers, step=3)

    def _execute_on_formation_EVERY_4(self, markers) -> List[int]:
        return self._sweep(markers, step=4)

    @staticmethod
    def _sort_by_axis(markers, *, axis: int) -> List[int]:
        with create_position_evaluator() as get_positions_of:
            coords = get_positions_of(markers)

        def key_func(x: int):
            return coords[x][axis]

        return sorted(range(len(markers)), key=key_func)

    @staticmethod
    def _sweep(markers, *, step: int) -> List[int]:
        num_markers = len(markers)
        if not num_markers or step < 2:
            return markers
        else:
            return sum(
                (list(range(start, num_markers, step)) for start in range(step)), []
            )
