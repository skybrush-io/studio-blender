import bpy

from bpy.props import BoolProperty, FloatProperty, IntProperty
from bpy.types import Operator

from numpy import array, column_stack, mgrid, repeat, tile, zeros
from typing import List

from sbstudio.model.types import Coordinate3D
from sbstudio.plugin.constants import Collections, Formations, Templates
from sbstudio.plugin.materials import (
    get_material_for_led_light_color,
    create_keyframe_for_diffuse_color_of_material,
)
from sbstudio.plugin.model.formation import add_points_to_formation, create_formation
from sbstudio.plugin.model.storyboard import get_storyboard
from sbstudio.plugin.operators.detach_materials_from_template import (
    detach_material_from_drone_template,
)
from sbstudio.plugin.selection import select_only
from sbstudio.plugin.utils import propose_names
from sbstudio.plugin.utils.bloom import enable_bloom_effect_if_needed

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
    center: Coordinate3D,
    rows: int = 1,
    columns: int = 1,
    num_drones_per_slot_row: int = 1,
    num_drones_per_slot_col: int = 1,
    spacing_row: float = 1,
    spacing_col: float = 1,
    intra_slot_spacing_row: float = 0.5,
    intra_slot_spacing_col: float = 0.5,
) -> List[Coordinate3D]:
    """Creates the points of a takeoff grid centered at the given coordinate.

    Parameters:
        center: the center of the takeoff grid
        rows: the number of rows in the grid
        columns: the number of columns in the grid
        num_drones_per_slot_row: the number of drones in a single grid slot row
        num_drones_per_slot_col: the number of drones in a single grid slot column
        spacing_row: the row spacing of points in the grid
        spacing_col: the column spacing of points in the grid
        intra_slot_spacing_row: the row spacing within a single slot of the grid
        intra_slot_spacing_col: the column spacing within a single slot of the grid

    Returns:
        the list of points in the grid
    """
    columns = max(columns, 0)
    rows = max(rows, 0)

    cx, cy, cz = center

    xs, ys = mgrid[0:columns, 0:rows]

    xs = (xs.ravel() - (columns - 1) / 2) * spacing_col + cx
    ys = (ys.ravel() - (rows - 1) / 2) * spacing_row + cy
    zs = cz + zeros(columns * rows)

    # At this point we have the coordinates of the cells in the grid. Replace
    # each cell with multiple drones if needed
    if num_drones_per_slot_row > 1 or num_drones_per_slot_col > 1:
        num_drones_per_slot = num_drones_per_slot_row * num_drones_per_slot_col
        # Calculate the ranges for x and y based on the number of drones
        x_range = [
            x - num_drones_per_slot_col // 2 for x in range(num_drones_per_slot_col)
        ]
        y_range = [
            y - num_drones_per_slot_row // 2 for y in range(num_drones_per_slot_row)
        ]

        # Adjust for even numbers to symmetrically distribute around the center
        if num_drones_per_slot_col % 2 == 0:
            x_range = [x + 0.5 for x in x_range]
        if num_drones_per_slot_row % 2 == 0:
            y_range = [y + 0.5 for y in y_range]

        slot_template = array(
            [
                [x * intra_slot_spacing_col, y * intra_slot_spacing_row]
                for y in y_range
                for x in x_range
            ]
        )
        template = column_stack((slot_template, zeros((len(slot_template), 1))))

        coords = repeat(column_stack((xs, ys, zs)), num_drones_per_slot, axis=0)
        coords += tile(template, (columns * rows, 1))
        xs, ys, zs = coords[:, 0], coords[:, 1], coords[:, 2]

    return list(zip(xs, ys, zs))


def _get_num_drones_per_slot(operator):
    return _get_num_drones_per_slot_row(operator) * _get_num_drones_per_slot_col(
        operator
    )


def _get_num_drones_per_slot_row(operator):
    if hasattr(operator, "drones_per_slot_row"):
        return max(1, operator.drones_per_slot_row)
    else:
        # backwards compatibility
        return 1


def _get_num_drones_per_slot_col(operator):
    if hasattr(operator, "drones_per_slot_col"):
        return max(1, operator.drones_per_slot_col)
    else:
        # backwards compatibility
        return 1


def _get_max_possible_drone_count(operator):
    return operator.rows * operator.columns * _get_num_drones_per_slot(operator)


def _ensure_rows_columns_and_counts_consistent(operator, context):
    max_possible_drone_count = _get_max_possible_drone_count(operator)
    num_drones = max_possible_drone_count - operator.empty_slots
    if num_drones < 1:
        operator.drones = 1
        operator.empty_slots = max(0, max_possible_drone_count)
    else:
        # condition needed to prevent recursion
        if operator.drones != num_drones:
            operator.drones = num_drones


def _handle_drone_count_change(operator, context):
    max_possible_drone_count = _get_max_possible_drone_count(operator)
    operator.empty_slots = max(0, max_possible_drone_count - operator.drones)
    _ensure_rows_columns_and_counts_consistent(operator, context)


def _handle_drones_per_slot_change(operator, context):
    _ensure_rows_columns_and_counts_consistent(operator, context)


class CreateTakeoffGridOperator(Operator):
    """Blender operator that creates the takeoff grid and the corresponding set
    of drones.
    """

    bl_idname = "skybrush.create_takeoff_grid"
    bl_label = "Create Takeoff Grid"
    bl_description = "Creates the takeoff grid and the corresponding set of drones"
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

    # Name is a misnomer, should be excess_drones, but we have to leave it
    # for sake of backward compatibility
    empty_slots = IntProperty(
        name="Number of drones that could be placed in the slots but are not needed",
        default=0,
        options={"HIDDEN"},
    )

    spacing = FloatProperty(
        name="Spacing",
        description="Spacing between the slots in the grid",
        default=3,
        soft_min=0,
        soft_max=50,
        unit="LENGTH",
    )

    use_advanced_settings = BoolProperty(
        name="Advanced",
        default=False,
        description="Advanced settings for creating the takeoff grid",
    )

    # advanced parameters below

    use_separate_column_spacing = BoolProperty(
        name="Use seperate column spacing",
        default=False,
        description="When checked, a separate column spacing will be used for the takeoff grid",
    )

    spacing_col = FloatProperty(
        name="Column spacing",
        description="Spacing between the columns of the slots in the grid",
        default=3,
        soft_min=0,
        soft_max=50,
        unit="LENGTH",
    )

    drones_per_slot_row = IntProperty(
        name="Intra-slot rows",
        description=("Number of rows in a single slot"),
        default=1,
        soft_min=1,
        soft_max=10,
        update=_handle_drones_per_slot_change,
    )

    drones_per_slot_col = IntProperty(
        name="Intra-slot columns",
        description=("Number of columns in a single slot"),
        default=1,
        soft_min=1,
        soft_max=10,
        update=_handle_drones_per_slot_change,
    )

    intra_slot_spacing_row = FloatProperty(
        name="Intra-slot row spacing",
        description="Row spacing between drones within each slot",
        default=0.5,
        soft_min=0,
        soft_max=5,
        unit="LENGTH",
    )

    intra_slot_spacing_col = FloatProperty(
        name="Intra-slot column spacing",
        description="Column spacing between drones within each slot",
        default=0.5,
        soft_min=0,
        soft_max=5,
        unit="LENGTH",
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        # general settings
        layout.prop(self, "rows")
        layout.prop(self, "columns")
        layout.prop(self, "drones")
        layout.prop(self, "spacing")
        layout.prop(self, "use_advanced_settings")
        # advanced settings
        if self.use_advanced_settings:
            # separate column spacing
            row = layout.row(heading="Column spacing")
            row.prop(self, "use_separate_column_spacing", text="")
            row = row.row()
            row.prop(self, "spacing_col", text="")
            row.enabled = self.use_separate_column_spacing
            # intra-slot parameters
            layout.prop(self, "drones_per_slot_row")
            layout.prop(self, "drones_per_slot_col")
            layout.prop(self, "intra_slot_spacing_row")
            layout.prop(self, "intra_slot_spacing_col")

    def execute(self, context):
        # This code path is invoked after an undo-redo
        self._run(context)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
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
            rows=self.rows,
            columns=self.columns,
            num_drones_per_slot_row=_get_num_drones_per_slot_row(self),
            num_drones_per_slot_col=_get_num_drones_per_slot_col(self),
            spacing_row=self.spacing,
            spacing_col=self.spacing_col
            if self.use_separate_column_spacing
            else self.spacing,
            intra_slot_spacing_row=self.intra_slot_spacing_row,
            intra_slot_spacing_col=self.intra_slot_spacing_col,
        )[: self.drones]

        settings = context.scene.skybrush.settings
        drone_template = Templates.find_drone(
            template=settings.drone_template,
            drone_radius=settings.drone_radius,
        )
        drone_collection = Collections.find_drones()

        template_material = get_material_for_led_light_color(drone_template)

        drones = []
        names = propose_names("Drone {}", len(points))
        for name, point in zip(names, points):
            drone = create_drone(
                location=point,
                name=name,
                template=drone_template,
                collection=drone_collection,
            )
            material = detach_material_from_drone_template(
                drone, template_material=template_material
            )

            # The next line is needed for light effects to work properly
            create_keyframe_for_diffuse_color_of_material(
                material, (1.0, 1.0, 1.0), frame=context.scene.frame_start, step=True
            )

            drones.append(drone)

        select_only(drones)

        enable_bloom_effect_if_needed()

        # Add a new storyboard entry with the initial formation if there is no
        # takeoff grid yet, or extend the existing grid with the new set of
        # points if there is one
        takeoff_grid = Formations.find_takeoff_grid(create=False)
        if not takeoff_grid:
            storyboard = get_storyboard(context=context)
            entry = storyboard.add_new_entry(
                formation=create_formation(Formations.TAKEOFF_GRID, points),
                frame_start=context.scene.frame_start,
                duration=0,
                select=True,
                context=context,
            )
            entry.update_mapping(list(range(len(points))))

        else:
            add_points_to_formation(takeoff_grid, points)
