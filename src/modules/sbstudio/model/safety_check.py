from dataclasses import dataclass, field

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
    max_acceleration: float = 4
    min_distance: float = 3
    max_velocity_z_up: float | None = None
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
            "maxAccelerationXY": round(self.max_acceleration, ndigits=ndigits),
            "maxAccelerationZ": round(self.max_acceleration, ndigits=ndigits),
            "minDistance": round(self.min_distance, ndigits=ndigits),
            "minNavAltitude": round(self.min_nav_altitude, ndigits=ndigits),
        }
        if self.max_velocity_z_up is not None:
            result["maxVelocityZUp"] = round(self.max_velocity_z_up, ndigits=ndigits)
        return result


@dataclass
class SafetyCheckResult:
    """Instances of this class hold the result of a single safety check."""

    drones_over_max_altitude: list[Coordinate3D] = field(default_factory=list)
    drones_over_max_velocity_xy: list[Coordinate3D] = field(default_factory=list)
    drones_over_max_velocity_z: list[Coordinate3D] = field(default_factory=list)
    drones_over_max_acceleration: list[Coordinate3D] = field(default_factory=list)
    drones_below_min_nav_altitude: list[Coordinate3D] = field(default_factory=list)
    closest_pair: tuple[Coordinate3D, Coordinate3D] | None = None
    min_distance: float | None = None
    min_altitude: float | None = None
    all_close_pairs: list[tuple[Coordinate3D, Coordinate3D]] = field(
        default_factory=list
    )

    def clear(self) -> None:
        self.drones_over_max_altitude.clear()
        self.drones_over_max_velocity_xy.clear()
        self.drones_over_max_velocity_z.clear()
        self.drones_over_max_acceleration.clear()
        self.drones_below_min_nav_altitude.clear()
        self.all_close_pairs.clear()
        self.closest_pair = None
        self.min_distance = None
        self.min_altitude = None
