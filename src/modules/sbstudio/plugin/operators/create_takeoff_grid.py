"""Blender operator that creates a regular rectangular takeoff grid."""

import bpy

from bpy.props import FloatProperty, IntProperty
from bpy.types import Operator
from numpy import mgrid, zeros
from typing import List

from sbstudio.model.types import Coordinate3D
from sbstudio.plugin.constants import Collections, Templates
from sbstudio.plugin.formation import create_formation
from sbstudio.plugin.selection import select_only
from sbstudio.plugin.utils import (
    propose_name,
    propose_names,
)

__all__ = ("CreateTakeoffGridOperator",)


def create_drone(location, *, name: str, template=None, collection=None):
    """Creates a new drone object at the given location.

    Parameters:
        location: the location where the drone should be created
        name: the name of the drone
        template: the template object to use for the mesh of the drone;
            `None` to use the default drone template
        collection: the collection that the drone should be a part of; use
            `None` to add it to the default drone collection
    """
    template = template or Templates.find_drone()
    collection = collection or Collections.find_drones()

    drone = template.copy()
    drone.data = template.data.copy()
    drone.name = name
    drone.location = location

    # The template might be hidden; let's make sure that we are visible even
    # if the template is hidden
    drone.hide_render = False
    drone.hide_select = False
    drone.hide_viewport = False

    collection.objects.link(drone)

    return drone


def create_points_of_takeoff_grid(
    center: Coordinate3D, spacing: float = 1, rows: int = 1, columns: int = 1
) -> List[Coordinate3D]:
    """Creates the points of a takeoff grid centered at the given coordinate.

    Parameters:
        center: the center of the takeoff grid
        spacing: the spacing of points within each row and column of the grid
        rows: the number of rows in the grid
        columns: the number of columns in the grid

    Returns:
        the list of points in the grid
    """
    columns = max(columns, 0)
    rows = max(rows, 0)

    cx, cy, cz = center

    xs, ys = mgrid[0:columns, 0:rows]

    xs = (xs.ravel() - (columns - 1) / 2) * spacing + cx
    ys = (ys.ravel() - (rows - 1) / 2) * spacing + cy
    zs = cz + zeros(columns * rows)

    return list(zip(xs, ys, zs))


def _ensure_rows_columns_and_counts_consistent(operator, context):
    num_drones = operator.rows * operator.columns - operator.empty_slots
    if num_drones < 1:
        operator.drones = 1
        operator.empty_slots = max(
            0, operator.rows * operator.columns - operator.drones
        )
    else:
        # condition needed to prevent recursion
        if operator.drones != num_drones:
            operator.drones = num_drones


def _handle_drone_count_change(operator, context):
    operator.empty_slots = max(0, operator.rows * operator.columns - operator.drones)
    _ensure_rows_columns_and_counts_consistent(operator, context)


class CreateTakeoffGridOperator(Operator):
    """Blender operator that creates a takeoff grid and optionally the
    corresponding set of drones.
    """

    bl_idname = "skybrush.create_takeoff_grid"
    bl_label = "Create Takeoff Grid"
    bl_options = {"REGISTER", "UNDO"}

    rows = IntProperty(
        name="Rows",
        description="Number of rows in the takeoff grid",
        default=10,
        soft_min=1,
        soft_max=100,
        update=_ensure_rows_columns_and_counts_consistent,
    )

    columns = IntProperty(
        name="Columns",
        description="Number of columns in the takeoff grid",
        default=10,
        soft_min=1,
        soft_max=100,
        update=_ensure_rows_columns_and_counts_consistent,
    )

    drones = IntProperty(
        name="Drone count",
        description="Number of drones in the grid",
        default=100,
        soft_min=1,
        soft_max=10000,
        update=_handle_drone_count_change,
    )

    empty_slots = IntProperty(
        name="Number of slots to leave empty", default=0, options={"HIDDEN"}
    )

    spacing = FloatProperty(
        name="Spacing",
        description="Spacing between the drones in the grid",
        default=3,
        soft_min=0,
        soft_max=50,
        unit="LENGTH",
    )

    def execute(self, context):
        # This code path is invoked after an undo-redo
        self._run(context)
        return {"FINISHED"}

    def invoke(self, context, event):
        # The code below is used to trigger the settings panel in the lower
        # left hand corner, see:
        #
        # https://blender.stackexchange.com/questions/191956/how-to-make-custom-create-options-panel-in-bottom-left
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        # This code path is invoked when the user triggers the operator
        self._run(context)
        return {"FINISHED"}

    def _run(self, context):
        bpy.ops.skybrush.prepare()

        points = create_points_of_takeoff_grid(
            center=context.scene.cursor.location,
            spacing=self.spacing,
            rows=self.rows,
            columns=self.columns,
        )[: self.drones]

        drone_template = Templates.find_drone()
        drone_collection = Collections.find_drones()

        name = propose_name("Takeoff formation {}", for_collection=True)
        create_formation(name, points)

        drones = []
        names = propose_names("Drone {}", len(points))
        for name, point in zip(names, points):
            drone = create_drone(
                location=point,
                name=name,
                template=drone_template,
                collection=drone_collection,
            )
            drones.append(drone)

        select_only(drone)
