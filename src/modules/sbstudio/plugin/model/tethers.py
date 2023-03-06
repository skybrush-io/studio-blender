from bpy.props import BoolProperty, FloatProperty
from bpy.types import Context, PropertyGroup
from math import pi
from typing import Optional, List, Sequence, overload

from sbstudio.model.tethers import TetherSafetyCheckResult
from sbstudio.model.types import Coordinate3D, LineSegment3D
from sbstudio.plugin.overlays import SafetyCheckOverlay, TetherOverlay

__all__ = ("TetherProperties",)

#: Global tether-specific safety-check overlay. This cannot be an attribute of
#  TetherProperties for some reason; Blender PropertyGroup objects are weird.
_safety_overlay = None

#: Global tether overlay. This cannot be an attribute of TetherProperties
#: for some reason; Blender PropertyGroup objects are weird.
_tether_overlay = None

#: Current tether-specific safety check result object. This cannot be an
# attribute of TetherProperties for some reason; Blender PropertyGroup objects
# are weird.
_safety_check_result = TetherSafetyCheckResult()


class TetherSafetyCheckOverlay(SafetyCheckOverlay):
    """Custom class for tether-specific safety checks."""

    def draw_2d(self) -> None:
        # overload parent's 2D drawing functionality not to get called twice;
        # 2d drawing is done in the safety check overlay, for tethers, too
        return


@overload
def _get_safety_overlay() -> TetherSafetyCheckOverlay:
    ...


@overload
def _get_safety_overlay(create: bool) -> Optional[TetherSafetyCheckOverlay]:
    ...


def _get_safety_overlay(create: bool = True):
    global _safety_overlay

    if _safety_overlay is None and create:
        # Lazy construction, this is intentional
        _safety_overlay = TetherSafetyCheckOverlay(
            marker_size=10, line_width=5, marker_color=(1, 0, 0.5, 1)
        )

    return _safety_overlay


@overload
def _get_tether_overlay() -> TetherOverlay:
    ...


@overload
def _get_tether_overlay(create: bool) -> Optional[TetherOverlay]:
    ...


def _get_tether_overlay(create: bool = True):
    global _tether_overlay

    if _tether_overlay is None and create:
        # Lazy construction, this is intentional
        _tether_overlay = TetherOverlay()

    return _tether_overlay


def angle_warning_enabled_updated(self, context: Optional[Context] = None):
    """Called when the tether angle warning is enabled or disabled by the user."""
    self.ensure_overlays_enabled_if_needed()
    self._refresh_overlays()


def angle_warning_threshold_updated(self, context: Optional[Context] = None):
    self._refresh_overlays()


def length_warning_enabled_updated(self, context: Optional[Context] = None):
    """Called when the tether length warning is enabled or disabled by the user."""
    self.ensure_overlays_enabled_if_needed()
    self._refresh_overlays()


def length_warning_threshold_updated(self, context: Optional[Context] = None):
    self._refresh_overlays()


def proximity_warning_enabled_updated(self, context: Optional[Context] = None):
    """Called when the tether proximity warning is enabled or disabled by the user."""
    self.ensure_overlays_enabled_if_needed()
    self._refresh_overlays()


def proximity_warning_threshold_updated(self, context: Optional[Context] = None):
    self._refresh_overlays()


class TetherProperties(PropertyGroup):
    """Property group that stores the parameters and calculated values of the
    real-time tether-specific safety checks.

    Some of the properties in this property group are calculated from the
    positions of the drones in the current frame and hence they are read-only
    to the user. Others represent parameters of the tethers and hence they can
    be modified by the user.
    """

    tethers = []
    """List of tethers in the current frame."""

    enabled = BoolProperty(
        name="Enable tethers and possibly safety checks between tethers",
        description=(
            "Enables tethers between the home position and the actual positions "
            "of drones. If enabled, tethers and possibly tether-specific safety"
            "might get calculated as well"
        ),
        default=False,
    )

    max_angle = FloatProperty(
        name="Max tether angle",
        description="Maximum angle deviation of tethers from vertical in the current frame",
        unit="ROTATION",
        default=0.0,
    )

    max_length = FloatProperty(
        name="Max tether length",
        description="Maximum length of tethers of all drones in the current frame",
        unit="LENGTH",
        default=0.0,
    )

    min_distance = FloatProperty(
        name="Min tether distance",
        description="Minimum distance between tethers of drones in the current frame",
        unit="LENGTH",
        default=0.0,
    )

    angle_warning_enabled = BoolProperty(
        name="Show tether angle warnings",
        description=(
            "Specifies whether Blender should show a warning when the angle of a "
            "tether is larger than the tether angle threshold"
        ),
        update=angle_warning_enabled_updated,
        default=True,
    )

    angle_warning_threshold = FloatProperty(
        name="Tether angle warning threshold",
        description="Maximum allowed tether angle for a single drone without triggering an tether angle warning",
        unit="ROTATION",
        default=pi / 9,
        min=0.0,
        soft_min=0.0,
        soft_max=pi / 2,
        update=angle_warning_threshold_updated,
    )

    length_warning_enabled = BoolProperty(
        name="Show tether length warnings",
        description=(
            "Specifies whether Blender should show a warning when the length of a "
            "tether is larger than the tether length threshold"
        ),
        update=length_warning_enabled_updated,
        default=True,
    )

    length_warning_threshold = FloatProperty(
        name="Tether length warning threshold",
        description="Maximum allowed tether length for a single drone without triggering an tether length warning",
        unit="LENGTH",
        default=50.0,
        min=0.0,
        soft_min=0.0,
        soft_max=200.0,
        update=length_warning_threshold_updated,
    )

    proximity_warning_enabled = BoolProperty(
        name="Show tether proximity warnings",
        description=(
            "Specifies whether Blender should show a warning when two tethers "
            "get closer than the tether distance threshold"
        ),
        update=proximity_warning_enabled_updated,
        default=True,
    )

    proximity_warning_threshold = FloatProperty(
        name="Tether proximity warning threshold",
        description="Minimum allowed distance between two tethers without "
        "triggering tether proximity warning",
        unit="LENGTH",
        default=5.0,
        min=0.0,
        soft_min=0.0,
        soft_max=50.0,
        update=proximity_warning_threshold_updated,
    )

    @property
    def max_angle_is_valid(self) -> bool:
        """Returns whether the maximum tether angle property can be considered
        valid. Right now we use zero to denote cases when there are no drones in
        the scene at all.
        """
        return self.max_angle > 0

    @property
    def max_length_is_valid(self) -> bool:
        """Returns whether the maximum tether length property can be considered
        valid. Right now we use zero to denote cases when there are no drones in
        the scene at all.
        """
        return self.max_length > 0

    @property
    def min_distance_is_valid(self) -> bool:
        """Returns whether the minimum proximity distance property can be
        considered valid. Right now we use zero to denote cases when there are
        no drones in the scene at all.
        """
        return self.min_distance > 0

    @property
    def should_show_angle_warning(self) -> bool:
        """Returns whether the tether angle warning should be drawn in the 3D
        view _right now_, given the current values of the properties.
        """
        return (
            self.angle_warning_enabled
            and self.max_angle_is_valid
            and self.max_angle > self.angle_warning_threshold
        )

    @property
    def should_show_length_warning(self) -> bool:
        """Returns whether the tether length warning should be drawn in the 3D
        view _right now_, given the current values of the properties.
        """
        return (
            self.length_warning_enabled
            and self.max_length_is_valid
            and self.max_length > self.length_warning_threshold
        )

    @property
    def should_show_proximity_warning(self) -> bool:
        """Returns whether the tether proximity warning should be drawn in the
        3D view _right now_, given the current values of the properties.
        """
        return (
            self.proximity_warning_enabled
            and self.min_distance_is_valid
            and self.min_distance < self.proximity_warning_threshold
        )

    def clear_tethers(self) -> None:
        """Clears tethers."""
        self.tethers = []

        self.clear_tether_safety_check_results()

    def clear_tether_safety_check_results(self) -> None:
        """Clear tether-specific safety checks."""
        global _safety_check_result

        self.max_angle = 0
        self.max_length = 0
        self.min_distance = 0

        _safety_check_result.clear()

        self._refresh_overlays()

    def ensure_overlays_enabled_if_needed(self) -> None:
        _get_tether_overlay().enabled = self.enabled
        _get_safety_overlay().enabled = self.enabled and (
            self.angle_warning_enabled
            or self.length_warning_enabled
            or self.proximity_warning_enabled
        )

    def update_tethers_and_safety_check_result(
        self,
        tethers: List[LineSegment3D],
        min_distance: Optional[float] = None,
        closest_points: Optional[LineSegment3D] = None,
        max_length: Optional[float] = None,
        tethers_over_max_length: Optional[List[LineSegment3D]] = None,
        max_angle: Optional[float] = None,
        tethers_over_max_angle: Optional[List[LineSegment3D]] = None,
    ) -> None:
        """Updates tethers and corresponding safety checks."""
        global _safety_check_result

        refresh = False

        if tethers:
            self.tethers = tethers
            refresh = True

        if min_distance is not None:
            self.min_distance = min_distance
            _safety_check_result.min_distance = min_distance
            refresh = True

        if closest_points is not None:
            _safety_check_result.closest_points = closest_points
            refresh = True

        if max_length is not None:
            self.max_length = max_length
            _safety_check_result.max_length = max_length
            refresh = True

        if tethers_over_max_length is not None:
            _safety_check_result.tethers_over_max_length = tethers_over_max_length
            refresh = True

        if max_angle is not None:
            self.max_angle = max_angle
            _safety_check_result.max_angle = max_angle
            refresh = True

        if tethers_over_max_angle is not None:
            _safety_check_result.tethers_over_max_angle = tethers_over_max_angle
            refresh = True

        if refresh:
            self.ensure_overlays_enabled_if_needed()
            self._refresh_overlays()

    def _refresh_overlays(self) -> None:
        """Refreshes tether-specific overlays on the 3D view if needed."""
        global _safety_check_result

        # refresh tether overlay
        overlay = _get_tether_overlay(create=False)

        if overlay:
            overlay.tethers = self.tethers

        # refresh tether-specific safety check overlay
        overlay = _get_safety_overlay(create=False)

        if overlay:
            markers: List[Sequence[Coordinate3D]] = []

            if (
                self.should_show_length_warning
                and _safety_check_result.tethers_over_max_length
            ):
                markers.extend(_safety_check_result.tethers_over_max_length)

            if (
                self.should_show_proximity_warning
                and _safety_check_result.closest_points is not None
            ):
                markers.append(_safety_check_result.closest_points)

            if (
                self.should_show_angle_warning
                and _safety_check_result.tethers_over_max_angle
            ):
                markers.extend(_safety_check_result.tethers_over_max_angle)

            overlay.markers = markers
