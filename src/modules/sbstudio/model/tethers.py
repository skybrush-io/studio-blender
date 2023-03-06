from dataclasses import dataclass, field
from typing import List, Optional

from .types import LineSegment3D

__all__ = (
    "TetherSafetyCheckParams",
    "TetherSafetyCheckResult",
)


@dataclass
class TetherSafetyCheckParams:
    """Tether-specific safety check parameters."""

    max_angle: float = 45
    """Maximum angle deviation from vertical in [deg]."""

    max_length: float = 50
    """Maximum length of tethers in [m]."""

    min_distance: float = 5
    """Minimum distance between tethers in [m]."""

    def as_dict(self, ndigits: int = 3):
        """Returns the tether-specific safety check parameters as a dictionary.

        Parameters:
            ndigits: round floats to this precision

        Return:
            dictionary representation of the tether-specific safety check
            parameters, rounded to the desired precision
        """
        result = {
            "maxAngle": round(self.max_angle, ndigits=ndigits),
            "maxLength": round(self.max_length, ndigits=ndigits),
            "minDistance": round(self.min_distance, ndigits=ndigits),
        }

        return result


@dataclass
class TetherSafetyCheckResult:
    """Instances of this class hold the result of a single tether-specific
    safety check."""

    max_angle: Optional[float] = None
    """Max measured angle in [rad]."""

    tethers_over_max_angle: List[LineSegment3D] = field(default_factory=list)
    """List of tethers over max angle."""

    max_length: Optional[float] = None
    """Max measured length in [m]."""

    tethers_over_max_length: List[LineSegment3D] = field(default_factory=list)
    """List of tethers over max length."""

    min_distance: Optional[float] = None
    """Min measured distance in [m]."""

    closest_points: Optional[LineSegment3D] = None
    """Closest two points between all tethers."""

    def clear(self) -> None:
        self.tethers_over_max_length.clear()
        self.tethers_over_max_angle.clear()
        self.closest_points = None
        self.min_distance = None
        self.max_angle = None
        self.max_length = None
