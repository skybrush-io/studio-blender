from bpy.props import FloatProperty, FloatVectorProperty, IntProperty
from bpy.types import MeshVertex

from math import inf
from numpy import ptp

from sbstudio.math.nearest_neighbors import find_nearest_neighbors
from sbstudio.plugin.model.formation import (
    get_markers_from_formation,
    get_world_coordinates_of_markers_from_formation,
)
from .base import FormationOperator

__all__ = ("GetFormationStatisticsOperator",)


class GetFormationStatisticsOperator(FormationOperator):
    """Shows an information dialog that indicates several useful properties of
    the currently selected formation.
    """

    bl_idname = "skybrush.get_formation_stats"
    bl_label = "Formation Statistics"
    bl_description = "Returns useful statistics about the currently selected formation in the Formations collection."
    bl_options = set({})

    marker_count = IntProperty(
        name="Total Size",
        description="Total number of targets in the formation, including simple meshes and vertex groups",
    )

    vertex_count = IntProperty(
        name="# Vertices",
        description="Number of vertices in all the meshes of the formation that are designated as targets",
    )

    empty_count = IntProperty(
        name="# Empties",
        description="Number of empties in all the meshes of the formation that are designated as targets",
    )

    nonempty_count = IntProperty(
        name="# Non-empties",
        description="Number of non-empties in all the meshes of the formation that are designated as targets",
    )

    size = FloatVectorProperty(
        name="Size",
        description="Size of the axis-aligned bounding box of the mesh in the current frame",
        subtype="TRANSLATION",
        precision=5,
    )

    min_distance = FloatProperty(
        name="Minimum distance",
        description="Minimum distance of any pair of points within the formation",
        subtype="DISTANCE",
        precision=4,
    )

    def invoke(self, context, event):
        formation = self.get_formation(context)

        if formation:
            markers = get_markers_from_formation(formation)
        else:
            markers = []

        if markers:
            coords = get_world_coordinates_of_markers_from_formation(formation)

            self.marker_count = len(markers)
            self.vertex_count = sum(
                1 for marker in markers if isinstance(marker, MeshVertex)
            )
            self.empty_count = sum(
                1
                for marker in markers
                if not isinstance(marker, MeshVertex)
                and getattr(marker, "type", None) == "EMPTY"
            )

            self.size = tuple(ptp(coords, axis=0))
            _, _, self.min_distance = find_nearest_neighbors(coords)
        else:
            self.marker_count = 0
            self.vertex_count = 0
            self.empty_count = 0
            self.size = (0, 0, 0)
            self.min_distance = inf

        self.nonempty_count = self.marker_count - self.vertex_count - self.empty_count

        return context.window_manager.invoke_props_dialog(self)

    def execute_on_formation(self, formation, context):
        # Nothing to do, the operator is display-only
        return {"FINISHED"}
