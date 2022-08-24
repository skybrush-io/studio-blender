from dataclasses import dataclass, field
from typing import List, Optional

Mapping = List[Optional[int]]
"""Type alias for mappings from drone indices to the corresponding target
marker indices.
"""


@dataclass
class TransitionPlan:
    """Response returned from a "plan transition" API request."""

    start_times: List[float] = field(default_factory=list)
    """The computed start times where the i-th item of the list contains the
    start time of the drone that will travel to the i-th target point.
    """

    durations: List[float] = field(default_factory=list)
    """The computed transition durations where the i-th item of the list
    contains the travel time of the drone that is assigned to the i-th
    target point.
    """

    mapping: Optional[List[Optional[int]]] = None
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
        return max(
            start_time + duration
            for start_time, duration in zip(self.start_times, self.durations)
        )
