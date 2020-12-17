from bpy.props import BoolProperty, FloatProperty, FloatVectorProperty
from bpy.types import Context, PropertyGroup
from typing import Optional

from sbstudio.plugin.overlays import SafetyCheckOverlay

__all__ = ("SafetyCheckProperties",)

#: Global safety check overlay. This cannot be an attribute of SafetyCheckProperties
#: for some reason; Blender PropertyGroup objects are weird.
overlay = None


def proximity_warning_enabled_updated(self, context: Optional[Context] = None):
    """Called when the proximity warning is enabled or disabled by the user."""
    global overlay

    if overlay is None:
        # Lazy construction, this is intentional
        overlay = SafetyCheckOverlay()

    overlay.enabled = self.proximity_warning_enabled
    self._refresh_overlay()


def proximity_warning_threshold_updated(self, context: Optional[Context] = None):
    self._refresh_overlay()


class SafetyCheckProperties(PropertyGroup):
    """Property group that stores the parameters and calculated values of the
    real-time flight safety checks.

    Some of the properties in this property group are calculated from the
    positions of the drones in the current frame and hence they are read-only
    to the user. Others represent parameters of the safety checks and hence
    they can be modified by the user.
    """

    min_distance = FloatProperty(
        name="Min distance",
        description="Minimum distance along all possible pairs of drones, calculated between their centers of mass",
        unit="LENGTH",
        default=0.0,
    )

    closest_pair_first = FloatVectorProperty(
        name="Location of the first point in the closest pair",
        options={"HIDDEN"},
        subtype="XYZ",
    )

    closest_pair_second = FloatVectorProperty(
        name="Location of the second point in the closest pair",
        options={"HIDDEN"},
        subtype="XYZ",
    )

    proximity_warning_enabled = BoolProperty(
        name="Show proximity warnings",
        description=(
            "Specifies whether Blender should show a warning in this panel when"
            " the minimum distance is less than the proximity warning threshold"
        ),
        update=proximity_warning_enabled_updated,
        default=True,
    )

    proximity_warning_threshold = FloatProperty(
        name="Proximity warning threshold",
        description="Minimum allowed distance between drones without triggering a proximity warning",
        unit="LENGTH",
        default=3.0,
        min=0.0,
        max=10.0,
        update=proximity_warning_threshold_updated,
    )

    @property
    def min_distance_is_valid(self) -> bool:
        """Retuns whether the minimum distance property can be considered valid.
        Right now we use zero to denote cases when there are no drones in the
        scene at all.
        """
        return self.min_distance > 0

    @property
    def should_show_proximity_warning(self) -> bool:
        """Returns whether the proximity warning should be drawn in the 3D view
        _right now_, given the current values of the properties.
        """
        return (
            self.proximity_warning_enabled
            and self.min_distance_is_valid
            and self.min_distance < self.proximity_warning_threshold
        )

    def clear_minimum_distance_calculation_result(self) -> None:
        """Clears the result of the last minimum distance calculation."""
        self.min_distance = 0
        self.closest_pair_first = (0, 0, 0)
        self.closest_pair_second = (0, 0, 0)
        self._refresh_overlay()

    def ensure_overlays_enabled_if_needed(self) -> None:
        proximity_warning_enabled_updated(self)

    def set_minimum_distance_calculation_result(
        self, first, second, distance: float
    ) -> None:
        """Clears the result of the last minimum distance calculation."""
        self.min_distance = distance
        self.closest_pair_first = first
        self.closest_pair_second = second
        self._refresh_overlay()

    def _refresh_overlay(self) -> None:
        """Refreshes the safety check overlay on the 3D view if needed."""
        global overlay
        if overlay:
            overlay.nearest_neighbor_coords = (
                [
                    self.closest_pair_first,
                    self.closest_pair_second,
                ]
                if self.min_distance_is_valid
                else None
            )
