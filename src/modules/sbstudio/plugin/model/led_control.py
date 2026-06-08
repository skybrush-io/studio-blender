from collections.abc import Sequence
from typing import overload

import bpy
from bpy.app.handlers import persistent
from bpy.props import EnumProperty
from bpy.types import Context, Object, PropertyGroup

from sbstudio.model.types import RGBAColor
from sbstudio.plugin.callbacks import final_color_updated_callbacks
from sbstudio.plugin.colors import set_color_of_drone
from sbstudio.plugin.overlays.leds import (
    LEDsOverlay,
    LEDsOverlayMarker,
)
from sbstudio.plugin.props import ColorProperty
from sbstudio.plugin.utils.evaluator import get_position_of_object
from sbstudio.plugin.views import find_current_3d_view

__all__ = ("LEDControlPanelProperties",)


_overlay = None
"""Global LEDs marker overlay. This cannot be an attribute of LEDControlPanelProperties
for some reason; Blender PropertyGroup objects are weird."""


def _visualization_callback_for_markers(
    drones: Sequence[Object], colors: Sequence[RGBAColor], has_active_effects: bool
) -> None:
    led_control = bpy.context.scene.skybrush.led_control
    if has_active_effects:
        overlay_markers = [
            (get_position_of_object(drone), color)
            for drone, color in zip(drones, colors, strict=True)
        ]
        led_control.update_overlay_markers(overlay_markers)
    else:
        led_control.clear_overlay_markers()


def _visualization_callback_for_materials(
    drones: Sequence[Object], colors: Sequence[RGBAColor], has_active_effects: bool
) -> None:
    if has_active_effects:
        for drone, color in zip(drones, colors, strict=True):
            set_color_of_drone(drone, color)

        # TODO: experiment with the "fast" solution below, which is actually slower for
        # the time being, but maybe there is a way to make it faster by calling the
        # proper update function...

        # from numpy import array, float32
        # from sbstudio.plugin.colors import set_colors_of_drones_fast

        # set_colors_of_drones_fast(drones, array(colors, dtype=float32).ravel())
        # for drone in drones:
        #     drone.update_tag()


@overload
def get_overlay() -> LEDsOverlay: ...


@overload
def get_overlay(create: bool) -> LEDsOverlay | None: ...


def get_overlay(create: bool = True):
    global _overlay

    if _overlay is None and create:
        _overlay = LEDsOverlay()

    return _overlay


def visualization_updated(
    self: "LEDControlPanelProperties", context: Context | None = None
):
    # unregister
    if self.visualization != "MARKERS":
        if final_color_updated_callbacks.ensure_missing(
            _visualization_callback_for_markers
        ):
            # TODO(vasarhelyi)
            self.clear_overlay_markers()

    if self.visualization != "MATERIALS":
        if final_color_updated_callbacks.ensure_missing(
            _visualization_callback_for_materials
        ):
            # TODO(vasarhelyi)
            # TODO: set drone colors back to base color without light effects if we are annoyed
            # by seeing material colors until the first frame change...
            pass

    # register
    match self.visualization:
        case "MARKERS":
            final_color_updated_callbacks.ensure(_visualization_callback_for_markers)
        case "MATERIALS":
            final_color_updated_callbacks.ensure(_visualization_callback_for_materials)

    # setup viewport shading according to selection
    space = find_current_3d_view(context)
    if space is not None:
        shading = space.shading
        if self.visualization == "MARKERS":
            shading.color_type = "MATERIAL"
            shading.wireframe_color_type = "THEME"
        else:
            shading.color_type = "OBJECT"
            shading.wireframe_color_type = "OBJECT"


class LEDControlPanelProperties(PropertyGroup):
    visualization = EnumProperty(
        items=[
            ("NONE", "None", "No rendering is very quick but invisible", 1),
            ("MARKERS", "Markers", "Markers are simple but quick", 2),
            ("MATERIALS", "Materials", "Material coloring looks nice but is slower", 3),
        ],
        name="Visualization",
        description=("The visualization method of the drone colors."),
        default="MATERIALS",
        update=visualization_updated,
    )
    """Visualization method of the drone colors."""

    primary_color = ColorProperty(
        name="Primary color", description="Primary color to set on the selected drones"
    )
    secondary_color = ColorProperty(
        name="Secondary color",
        description="Secondary color to set on the selected drones; used for gradients only",
        default=(0, 0, 0),
    )

    def clear_overlay_markers(self) -> None:
        """Clears the light effect overlay markers."""
        self.ensure_overlays_enabled_if_needed()

        overlay = get_overlay(create=False)
        if overlay:
            overlay.markers = []

    def ensure_overlays_enabled_if_needed(self) -> None:
        get_overlay().enabled = self.visualization == "MARKERS"

    def update_overlay_markers(self, markers: Sequence[LEDsOverlayMarker]) -> None:
        """Updates the light effect overlay markers."""
        self.ensure_overlays_enabled_if_needed()

        overlay = get_overlay(create=False)
        if overlay:
            overlay.markers = markers

    def swap_colors(self):
        primary, secondary = self.primary_color.copy(), self.secondary_color.copy()
        self.primary_color, self.secondary_color = secondary, primary


@persistent
def _on_load_initialize_callbacks(*args):
    scene = bpy.context.scene
    if hasattr(scene, "skybrush") and hasattr(scene.skybrush, "led_control"):
        visualization_updated(scene.skybrush.led_control)


def register():
    """Registers LED control subsystem."""
    if _on_load_initialize_callbacks not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load_initialize_callbacks)


def unregister():
    """Unregisters LED control subsystem."""
    if _on_load_initialize_callbacks in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_initialize_callbacks)

    final_color_updated_callbacks.ensure_missing(_visualization_callback_for_markers)
    final_color_updated_callbacks.ensure_missing(_visualization_callback_for_materials)
