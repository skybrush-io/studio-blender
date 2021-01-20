from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .types import Coordinate3D

__all__ = (
    "SafetyCheckParams",
    "SafetyCheckResult",
)


@dataclass
class SafetyCheckParams:
    """Safety check parameters."""

    max_altitude: float = 150
    max_velocity_xy: float = 8
    max_velocity_z: float = 3
    min_distance: float = 3

    def as_dict(self, ndigits: int = 3):
        """Return self as a dictionary.

        Parameters:
            ndigits: round floats to this precision

        Return:
            dictionary of self rounded to the desired precision
        """
        return {
            "max_altitude": round(self.max_altitude, ndigits=ndigits),
            "max_velocity_xy": round(self.max_velocity_xy, ndigits=ndigits),
            "max_velocity_z": round(self.max_velocity_z, ndigits=ndigits),
            "min_distance": round(self.min_distance, ndigits=ndigits),
        }


@dataclass
class SafetyCheckResult:
    """Instances of this class hold the result of a single safety check."""

    drones_over_max_altitude: List[Coordinate3D] = field(default_factory=list)
    drones_over_max_velocity_xy: List[Coordinate3D] = field(default_factory=list)
    drones_over_max_velocity_z: List[Coordinate3D] = field(default_factory=list)
    closest_pair: Optional[Tuple[Coordinate3D, Coordinate3D]] = None
    min_distance: Optional[float] = None

    def clear(self) -> None:
        self.drones_over_max_altitude.clear()
        self.drones_over_max_velocity_xy.clear()
        self.drones_over_max_velocity_z.clear()
        self.closest_pair = None
        self.min_distance = None
