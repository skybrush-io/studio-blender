from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .types import Coordinate3D

__all__ = ("SafetyCheckResult",)


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
