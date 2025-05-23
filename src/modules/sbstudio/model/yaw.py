from dataclasses import dataclass
from operator import attrgetter
from typing import (
    Sequence,
    TypeVar,
)

__all__ = (
    "YawSetpointList",
    "YawSetpoint",
)


C = TypeVar("C", bound="YawSetpointList")


@dataclass
class YawSetpoint:
    """The simplest representation of a yaw setpoint."""

    time: float
    """The timestamp associated to the yaw setpoint, in seconds."""

    angle: float
    """The yaw angle associated to the yaw setpoint, in degrees, CW."""


class YawSetpointList:
    """Simplest representation of a causal yaw setpoint list in time.

    Setpoints are assumed to be linear, i.e. yaw rate is constant
    between setpoints.
    """

    def __init__(self, setpoints: Sequence[YawSetpoint] = []):
        self.setpoints = sorted(setpoints, key=attrgetter("time"))

    def append(self, setpoint: YawSetpoint) -> None:
        """Add a setpoint to the end of the setpoint list."""
        if self.setpoints and self.setpoints[-1].time >= setpoint.time:
            raise ValueError("New setpoint must come after existing setpoints in time")
        self.setpoints.append(setpoint)

    def as_dict(self, ndigits: int = 3):
        """Create a Skybrush-compatible dictionary representation of this
        instance.

        Parameters:
            ndigits: round floats to this precision

        Return:
            dictionary of this instance, to be converted to JSON later
        """
        return {
            "setpoints": [
                [
                    round(setpoint.time, ndigits=ndigits),
                    round(setpoint.angle, ndigits=ndigits),
                ]
                for setpoint in self.setpoints
            ],
            "version": 1,
        }

    def shift_in_place(
        self: C,
        delta: float,
    ) -> C:
        """Translates the yaw setpoints with the given delta angle. The
        setpoint list will be manipulated in-place.

        Args:
            delta: the translation angle

        Returns:
            the shifted yaw setpoint list
        """
        for setpoint in self.setpoints:
            setpoint.angle += delta
        return self

    def shift_time_in_place(self: C, delta: float) -> C:
        """Shifts all timestamps of the yaw setpoints in-place.

        Parameters:
            delta: the time delta to add to the timestamp of each setpoint
        """
        for setpoint in self.setpoints:
            setpoint.time += delta
        return self

    def simplify(self: C) -> C:
        """Simplify yaw setpoints in place.

        Returns:
            the simplified yaw setpoint list
        """
        if not self.setpoints:
            return self

        # set first yaw in the [0, 360) range and shift entire list accordingly
        angle = self.setpoints[0].angle % 360
        delta = angle - self.setpoints[0].angle
        if delta:
            self.shift_in_place(delta)

        # remove intermediate points on constant angular speed segments
        new_setpoints: list[YawSetpoint] = []
        last_angular_speed = -1e12
        for setpoint in self.setpoints:
            if not new_setpoints:
                new_setpoints.append(setpoint)
            else:
                dt = setpoint.time - new_setpoints[-1].time
                if dt <= 0:
                    raise RuntimeError(
                        f"Yaw timestamps are not causal ({setpoint.time} <= {new_setpoints[-1].time})"
                    )
                # when calculating angular speed, we round timestamps and angles
                # to avoid large numeric errors at division by small numbers
                angular_speed = (
                    round(setpoint.angle, ndigits=3)
                    - round(new_setpoints[-1].angle, ndigits=3)
                ) / round(dt, ndigits=3)
                if abs(angular_speed - last_angular_speed) < 1e-6:
                    new_setpoints[-1] = setpoint
                else:
                    new_setpoints.append(setpoint)
                last_angular_speed = angular_speed

        self.setpoints = new_setpoints

        return self

    def unwrap(self: C, *, threshold: float = 180, full_cycle: float = 360) -> C:
        """Unwraps the yaw angles of the setpoint list "in-place" and ensures
        that consecutive sampled angles never have a difference of more than
        180 degrees.
        """
        for prev, curr in zip(self.setpoints, self.setpoints[1:]):
            diff = curr.angle - prev.angle
            if diff > threshold or diff < -threshold:
                num_cycles = -round(diff / full_cycle)
                curr.angle += num_cycles * full_cycle

        return self
