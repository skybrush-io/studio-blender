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
    max_velocity_z_up: Optional[float] = None
    min_nav_altitude: float = 2.5

    def as_dict(self, ndigits: int = 3):
        """Returns the safety check parameters as a dictionary.

        Parameters:
            ndigits: round floats to this precision

        Return:
            dictionary representation of the safety check parameters, rounded to
            the desired precision
        """
        result = {
            "maxAltitude": round(self.max_altitude, ndigits=ndigits),
            "maxVelocityXY": round(self.max_velocity_xy, ndigits=ndigits),
            "maxVelocityZ": round(self.max_velocity_z, ndigits=ndigits),
            "minDistance": round(self.min_distance, ndigits=ndigits),
            "minNavAltitude": round(self.min_nav_altitude, ndigits=ndigits),
        }
        if self.max_velocity_z_up is not None:
            result["maxVelocityZUp"] = round(self.max_velocity_z_up, ndigits=ndigits)
        return result


@dataclass
class SafetyCheckResult:
    """Instances of this class hold the result of a single safety check."""

    drones_over_max_altitude: List[Coordinate3D] = field(default_factory=list)
    drones_over_max_velocity_xy: List[Coordinate3D] = field(default_factory=list)
    drones_over_max_velocity_z: List[Coordinate3D] = field(default_factory=list)
    drones_below_min_nav_altitude: List[Coordinate3D] = field(default_factory=list)
    closest_pair: Optional[Tuple[Coordinate3D, Coordinate3D]] = None
    min_distance: Optional[float] = None
    min_altitude: Optional[float] = None
    all_close_pairs: List[Tuple[Coordinate3D, Coordinate3D]] = field(
        default_factory=list
    )

    def clear(self) -> None:
        self.drones_over_max_altitude.clear()
        self.drones_over_max_velocity_xy.clear()
        self.drones_over_max_velocity_z.clear()
        self.drones_below_min_nav_altitude.clear()
        self.all_close_pairs.clear()
        self.closest_pair = None
        self.min_distance = None
        self.min_altitude = None
