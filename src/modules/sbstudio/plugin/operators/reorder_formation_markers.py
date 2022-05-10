from numpy import array, logical_or
from numpy.linalg import norm
from natsort import index_natsorted, order_by_index
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
            ("NAME", "Sort by name", "", 1),
            ("SHUFFLE", "Shuffle", "", 2),
            ("REVERSE", "Reverse", "", 3),
            ("X", "Sort by X coordinate", "", 4),
            ("Y", "Sort by Y coordinate", "", 5),
            ("Z", "Sort by Z coordinate", "", 6),
            ("EVERY_2", "Every 2nd", "", 7),
            ("EVERY_3", "Every 3rd", "", 8),
            ("EVERY_4", "Every 4th", "", 9),
            ("ENSURE_SAFETY_DISTANCE", "Ensure safety distance", "", 10),
        ],
        name="Type",
        description="Reordering to perform on the formation",
        default="NAME",
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
            index_vector: List[int] = func(markers, context)
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

    def _execute_on_formation_NAME(self, markers, context) -> List[int]:
        """Sort markers by their names. This essentially allows the user to
        specify a custom order by naming the markers appropriately.

        Sorting is done according to natural sort so the user will not have to
        prepend zeroes to numbers to get the right sort order.
        """
        names = [str(getattr(marker, "name", "")) for marker in markers]
        index = index_natsorted(names)
        return order_by_index(list(range(len(markers))), index)  # type: ignore

    def _execute_on_formation_SHUFFLE(self, markers, context) -> List[int]:
        """Shuffle markers in random order."""
        mapping = list(range(len(markers)))
        shuffle(mapping)
        return mapping

    def _execute_on_formation_REVERSE(self, markers, context) -> List[int]:
        """Reverse the current order of the markers."""
        return list(reversed(range(len(markers))))

    def _execute_on_formation_X(self, markers, context) -> List[int]:
        """Stable-sort markers by their X coordinates."""
        return self._sort_by_axis(markers, axis=0)

    def _execute_on_formation_Y(self, markers, context) -> List[int]:
        """Stable-sort markers by their Y coordinates."""
        return self._sort_by_axis(markers, axis=1)

    def _execute_on_formation_Z(self, markers, context) -> List[int]:
        """Stable-sort markers by their Z coordinates."""
        return self._sort_by_axis(markers, axis=2)

    def _execute_on_formation_EVERY_2(self, markers, context) -> List[int]:
        """Step to every second marker."""
        return self._sweep(markers, step=2)

    def _execute_on_formation_EVERY_3(self, markers, context) -> List[int]:
        """Step to every third marker."""
        return self._sweep(markers, step=3)

    def _execute_on_formation_EVERY_4(self, markers, context) -> List[int]:
        """Step to every fourth marker."""
        return self._sweep(markers, step=4)

    def _execute_on_formation_ENSURE_SAFETY_DISTANCE(
        self, markers, context
    ) -> List[int]:
        """Traverse the markers in the current order, skipping over markers
        that are closer to any of the previous markers in the current sweep than
        the safety distance. Start new sweeps until all markers are selected.
        """
        num_markers = len(markers)
        if not num_markers:
            return []

        with create_position_evaluator() as get_positions_of:
            coords = array(get_positions_of(markers))

        queue: List[int] = list(range(num_markers))
        masked = array([False] * num_markers, dtype=bool)
        skipped: List[int] = []
        result: List[int] = []

        dist_threshold: float = (
            context.scene.skybrush.safety_check.proximity_warning_threshold
        )

        while queue:
            # Reset the mask
            masked.fill(False)

            for marker_index in queue:
                if masked[marker_index]:
                    # This marker is masked already because it is too close to
                    # a point chosen earlier in this sweep
                    skipped.append(marker_index)
                else:
                    # Choose this marker and mask all markers that are closer to
                    # this than the distance threshold
                    closer = (
                        norm(coords - coords[marker_index], axis=1) < dist_threshold
                    )
                    closer[marker_index] = False
                    logical_or(masked, closer, out=masked)
                    result.append(marker_index)

            queue.clear()
            if skipped:
                queue.extend(skipped)
                skipped.clear()

        return result

    @staticmethod
    def _sort_by_axis(markers, *, axis: int) -> List[int]:
        """Stable-sort markers by a given axis."""
        with create_position_evaluator() as get_positions_of:
            coords = get_positions_of(markers)

        def key_func(x: int):
            return coords[x][axis]

        return sorted(range(len(markers)), key=key_func)

    @staticmethod
    def _sweep(markers, *, step: int) -> List[int]:
        """Take the current order and start jumping to every n-th marker from
        the beginning, looping back to the first unused marker when reaching
        the end of the sequence.
        """
        num_markers = len(markers)
        if not num_markers or step < 2:
            return markers
        else:
            return sum(
                (list(range(start, num_markers, step)) for start in range(step)), []
            )
