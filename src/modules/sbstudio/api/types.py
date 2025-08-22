from dataclasses import dataclass, field
from functools import total_ordering
from math import inf
from re import compile, fullmatch
from typing import Any, List, Optional

Mapping = list[Optional[int]]
"""Type alias for mappings from drone indices to the corresponding target
marker indices.
"""


@dataclass
class Limits:
    """Response returned from a "query limits" API request."""

    num_drones: float = inf
    """Number of drones supported by the server. Infinity is allowed."""

    features: List[str] = field(default_factory=list)
    """List of feature tags returned by the server."""

    @classmethod
    def default(cls):
        """Returns a limits object to be used at startup."""
        return Limits()

    @classmethod
    def from_json(cls, obj: Any):
        if not isinstance(obj, dict):
            raise TypeError("limits object can only be constructed from a dict")

        num_drones = obj.get("num_drones")
        if num_drones is None:
            num_drones = inf
        elif isinstance(num_drones, int):
            # This is OK
            pass
        elif isinstance(num_drones, float) and num_drones.is_integer():
            num_drones = int(num_drones)
        else:
            raise TypeError("invalid type for num_drones")

        features = obj.get("features")
        if features is None:
            features = []
        elif hasattr(features, "__iter__"):
            features = [str(feature) for feature in features]
        else:
            raise TypeError("invalid type for features")

        return cls(num_drones=num_drones, features=sorted(set(features)))


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

    @property
    def duration(self) -> float:
        """Returns the overall duration of the smart RTH plan in seconds."""
        if not self.start_times or not self.durations:
            return 0

        return max(
            start + duration
            for start, duration in zip(self.start_times, self.durations, strict=True)
        )


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

    mapping: Optional[Mapping] = None
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


_SEMVER_REGEX = compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
"""Regex pattern for a semantic version string, inherited from
https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
"""


@total_ordering
@dataclass(frozen=True)
class Version:
    """Response returned from a "query version" API request,
    i.e., a semantic version number."""

    major: int
    minor: int
    patch: int
    pre_release: str | None = None
    build_metadata: str | None = None

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            raise TypeError(f"Cannot compare object of type Version and {type(other)}")

        if (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        ):
            return True

        # TODO: if we need to compare pre_releases more accurately,
        # we can extend this comparison below based on our pre-release
        # naming convention later on, once we have one. For the time
        # being we only treat pre-releases earlier than normal releases.
        return bool(self.pre_release and not other.pre_release)

    def __str__(self):
        retval = f"{self.major}.{self.minor}.{self.patch}"

        if self.pre_release:
            retval += f"-{self.pre_release}"

        if self.build_metadata:
            retval += f"+{self.build_metadata}"

        return retval

    @classmethod
    def from_json(cls, obj: Any):
        if not isinstance(obj, dict):
            raise TypeError("version object can only be constructed from a dict")

        version = obj.get("version")
        if version is None:
            raise TypeError("version object does not contain version string")

        return cls.from_string(version)

    @classmethod
    def from_string(cls, version_str: str):
        """Parses a semantic version from its string representation."""
        match = fullmatch(_SEMVER_REGEX, version_str.strip())
        if not match:
            raise ValueError(f"Invalid version string: {version_str}")
        major = int(match.group("major"))
        minor = int(match.group("minor"))
        patch = int(match.group("patch"))
        pre_release = match.group("prerelease")
        build_metadata = match.group("buildmetadata")

        return cls(major, minor, patch, pre_release, build_metadata)

    def to_tuple(self):
        return (
            self.major,
            self.minor,
            self.patch,
            self.pre_release,
            self.build_metadata,
        )
