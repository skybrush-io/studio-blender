from typing import overload

from bpy.props import EnumProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import Context, PropertyGroup

from sbstudio.plugin.constants import NUM_PYRO_CHANNELS, Collections
from sbstudio.plugin.overlays.pyro import (
    PyroOverlay,
    PyroOverlayInfo,
    PyroOverlayMarker,
)
from sbstudio.plugin.utils.pyro_markers import update_pyro_particles_of_object

__all__ = ("PyroControlPanelProperties",)

#: Global pyro marker overlay. This cannot be an attribute of PyroControlPanelProperties
#: for some reason; Blender PropertyGroup objects are weird.
_overlay = None


@overload
def get_overlay() -> PyroOverlay: ...


@overload
def get_overlay(create: bool) -> PyroOverlay | None: ...


def get_overlay(create: bool = True):
    global _overlay

    if _overlay is None and create:
        _overlay = PyroOverlay()

    return _overlay


def visualization_updated(
    self: "PyroControlPanelProperties", context: Context | None = None
):
    """Called when user changes the visualization type of pyro effects."""
    drones = Collections.find_drones(create=False)

    if not drones:
        return

    for drone in drones.objects:
        update_pyro_particles_of_object(drone)


class PyroControlPanelProperties(PropertyGroup):
    visualization = EnumProperty(
        items=[
            ("NONE", "None", "No rendering is very quick but invisible", 1),
            ("MARKERS", "Markers", "Markers are simple but quick", 2),
            ("PARTICLES", "Particles", "Particles are spectacular but slow", 3),
            ("INFO", "Info", "Static pyro info for aiding pre-flight handling", 4),
        ],
        name="Visualization",
        description=("The visualization method of the pyro effect."),
        default="MARKERS",
        update=visualization_updated,
    )

    channel = IntProperty(
        name="Channel",
        description="The (1-based) channel index the pyro is attached to",
        default=1,
        min=1,
        max=NUM_PYRO_CHANNELS,
    )

    # pyro payload properties

    name = StringProperty(
        name="Name",
        description="Name of the pyro effect to trigger",
        default="30s Gold Glittering Gerb",
    )

    duration = FloatProperty(
        name="Duration",
        description="The duration of the pyro effect",
        default=30,
        min=0.1,
        unit="TIME",
        step=100,  # button step is 1/100th of step
    )

    prefire_time = FloatProperty(
        name="Prefire time",
        description="The time needed for the pyro effect to show up after it gets triggered",
        min=0,
        unit="TIME",
        step=100,  # button step is 1/100th of step
    )

    # TODO: add yaw and pitch angle relative to the drone, if needed

    def clear_pyro_overlay_markers(self) -> None:
        """Clears the pyro overlay markers."""
        self.ensure_overlays_enabled_if_needed()

        overlay = get_overlay(create=False)
        if overlay:
            overlay.markers = []

    def ensure_overlays_enabled_if_needed(self) -> None:
        get_overlay().enabled = self.visualization in ["MARKERS", "INFO"]

    def update_pyro_overlay_markers(self, markers: list[PyroOverlayMarker]) -> None:
        """Updates the pyro overlay markers."""
        self.ensure_overlays_enabled_if_needed()

        overlay = get_overlay(create=False)
        if overlay:
            overlay.markers = markers

    def update_pyro_overlay_info_blocks(
        self, info_blocks: list[PyroOverlayInfo]
    ) -> None:
        """Updates the pyro overlay info blocks."""
        self.ensure_overlays_enabled_if_needed()

        overlay = get_overlay(create=False)
        if overlay:
            overlay.info_blocks = info_blocks
