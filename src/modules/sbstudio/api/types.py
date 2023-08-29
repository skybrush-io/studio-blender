from dataclasses import dataclass, field
from typing import Optional

Mapping = list[Optional[int]]
"""Type alias for mappings from drone indices to the corresponding target
marker indices.
"""


@dataclass
class SmartRTHPlan:
    """Response returned from a "plan smart RTH" API request."""

    start_times: list[float] = field(default_factory=list)
    """The computed start times where the i-th item of the list contains the
    start time of the drone that will travel to the i-th target point [s].
    """

    durations: list[float] = field(default_factory=list)
    """The computed smart RTH durations where the i-th item of the list
    contains the travel time of the drone that is assigned to the i-th
    target point [s].
    """

    inner_points: list[list[list[float]]] = field(default_factory=list)
    """The inner points of the smart RTH transition if it is not a
    straight line transition, where the i-th item of the main list
    contains the inner points of the drone that is assigned to the i-th
    target point. Points are represented in [t, x, y, z] order."""

    @classmethod
    def empty(cls):
        return cls(start_times=[], durations=[], inner_points=[])


@dataclass
class TransitionPlan:
    """Response returned from a "plan transition" API request."""

    start_times: list[float] = field(default_factory=list)
    """The computed start times where the i-th item of the list contains the
    start time of the drone that will travel to the i-th target point.
    """

    durations: list[float] = field(default_factory=list)
    """The computed transition durations where the i-th item of the list
    contains the travel time of the drone that is assigned to the i-th
    target point.
    """

    mapping: Optional[list[Optional[int]]] = None
    """The computed matching where the i-th item of the list contains the
    index of the source point that the i-th target point is mapped to, or
    ``None`` if the given target point is left unmatched. Omitted if the
    initial request specified a fixed matching.
    """

    clearance: Optional[float] = None
    """The minimum distance across all straight-line trajectories between the
    source and target points of the mapping, after deducting the radii of the
    drones. Omitted if the request did not specify the radii or if there were
    no points to match.
    """

    @classmethod
    def empty(cls):
        return cls(mapping=[])

    @property
    def total_duration(self) -> float:
        return (
            max(
                start_time + duration
                for start_time, duration in zip(self.start_times, self.durations)
            )
            if self.start_times and self.durations
            else 0.0
        )
