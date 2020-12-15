from bpy.props import BoolProperty, EnumProperty
from bpy.types import Operator
from random import shuffle

from sbstudio.plugin.actions import ensure_action_exists_for_object
from sbstudio.plugin.keyframes import set_keyframes
from sbstudio.plugin.materials import (
    get_material_for_led_light_color,
    get_shader_node_and_input_for_diffuse_color_of_material,
)
from sbstudio.plugin.props import ColorProperty
from sbstudio.plugin.selection import get_selected_drones
from sbstudio.plugin.utils.evaluator import create_position_evaluator

__all__ = ("ApplyColorsToSelectedDronesOperator",)


class ApplyColorsToSelectedDronesOperator(Operator):
    """Swaps the current primary and secondary colors in the LED control panel."""

    bl_idname = "skybrush.apply_colors_to_selection"
    bl_label = "Apply Colors to Selected Drones"
    bl_description = (
        "Applies the current primary or secondary color from the LED control "
        "panel to the selected drones, optionally creating a gradient."
    )
    bl_options = {"REGISTER", "UNDO"}

    primary_color = ColorProperty(
        name="Primary color",
        description="Primary color to apply on the selected drones",
    )

    secondary_color = ColorProperty(
        name="Secondary color",
        description="Secondary color to apply on the selected drones; used for gradients only",
        default=(0, 0, 0),
    )

    color = EnumProperty(
        name="Color to apply",
        items=[
            ("PRIMARY", "Primary (1)", "", 1),
            ("SECONDARY", "Secondary (2)", "", 2),
            ("GRADIENT", "Gradient (1 -> 2)", "", 3),
        ],
        default="PRIMARY",
    )

    fade = BoolProperty(
        name="Fade to color",
        description="Add a keyframe to fade to this color from the previous keyframe instead of stepping to this color abruptly",
        default=False,
    )

    gradient_mode = EnumProperty(
        name="Order in gradient",
        items=[
            ("SELECTION", "Selection", "", 1),
            ("RANDOM", "Random", "", 2),
            ("X", "X coordinate", "", 3),
            ("Y", "Y coordinate", "", 4),
            ("Z", "Z coordinate", "", 5),
            ("DISTANCE", "Distance from 3D cursor", "", 6),
        ],
        default="DISTANCE",
    )

    def execute(self, context):
        # This code path is invoked after an undo-redo
        self._run(context)
        return {"FINISHED"}

    def invoke(self, context, event):
        # Inherit the colors from the LED control panel
        led_control = context.scene.skybrush.led_control

        self.primary_color = led_control.primary_color.copy()
        self.secondary_color = led_control.secondary_color.copy()

        if event.type == "LEFTMOUSE":
            # We are being invoked from a button in the LED control panel.
            # Move on straight to the execution phase.
            return self.execute(context)
        else:
            # We are probably being invoked from the Blender command palette
            # so show the props dialog.
            return context.window_manager.invoke_props_dialog(self)

    def _run(self, context):
        selection = get_selected_drones()
        num_selected = len(selection)
        if not num_selected:
            return

        selection = self._sort_selection(selection, context)

        frame = context.scene.frame_current
        for index, drone in enumerate(selection):
            self._apply_color_to_single_drone(
                drone, frame, index, index / (num_selected - 1)
            )

    def _sort_selection(self, selection, context):
        """Sorts the list of selected drones in gradient mode, based on the
        order selected by the user.
        """
        if self.color != "GRADIENT":
            return selection

        if self.gradient_mode == "RANDOM":
            shuffle(selection)
            return selection

        with create_position_evaluator() as get_positions_of:
            positions = get_positions_of(selection)

        if self.gradient_mode == "X":
            priorities = [point[0] for point in positions]
        elif self.gradient_mode == "Y":
            priorities = [point[1] for point in positions]
        elif self.gradient_mode == "Z":
            priorities = [point[2] for point in positions]
        elif self.gradient_mode == "DISTANCE":
            origin = tuple(context.scene.cursor.location)
            priorities = [
                (origin[0] - point[0]) ** 2
                + (origin[1] - point[1]) ** 2
                + (origin[2] - point[2]) ** 2
                for point in positions
            ]

        order = list(range(len(selection)))
        order.sort(key=priorities.__getitem__)

        return [selection[i] for i in order]

    def _apply_color_to_single_drone(self, drone, frame: int, index: int, ratio: float):
        material = get_material_for_led_light_color(drone)
        if not material:
            # Drone does not have an LED light
            return

        # Ensure that we have animation data for the shader node tree. we need
        # to use a custom name because all the node trees otherwise have the
        # same name ("Shader Nodetree") so they would get the same action
        node_tree = material.node_tree
        ensure_action_exists_for_object(
            node_tree, name=f"{material.name} Shader Nodetree Action"
        )

        # Create the color to add in the keyframes
        if self.color == "PRIMARY":
            # Pure primary color
            color = self.primary_color
        elif self.color == "SECONDARY":
            # Pure secondary color
            color = self.secondary_color
        else:
            # Gradient
            color = self.primary_color * (1 - ratio) + self.secondary_color * ratio

        color_as_rgba = color.r, color.g, color.b, 1.0
        keyframes = [(frame, color_as_rgba)]
        if not self.fade:
            keyframes.insert(0, (frame - 1, None))

        # Set the keyframes
        node, input = get_shader_node_and_input_for_diffuse_color_of_material(material)
        index = node.inputs.find(input.name)
        data_path = f'nodes["{node.name}"].inputs[{index}].default_value'
        set_keyframes(node_tree, data_path, keyframes, interpolation="LINEAR")
