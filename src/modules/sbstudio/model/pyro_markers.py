from dataclasses import asdict, dataclass, field
from json import dumps, loads

from typing import Any

__all__ = ("PyroMarkers", "PyroPayload")


@dataclass
class PyroPayload:
    """Properties of a pyro payload that we store and use."""

    name: str
    """Name of the pyro effect to trigger."""

    duration: float = 30
    """The overall duration of the pyro effect, in seconds."""

    prefire_time: float = 0
    """Time needed for the pyro payload to show up after ignition, in seconds."""


@dataclass
class PyroMarker:
    """Descriptor of a single pyro trigger event
    on a specific drone's specific pyro channel.

    So far we assume that one channel can be used only once for pyro triggering."""

    frame: int
    """The frame number of the trigger event."""

    payload: PyroPayload
    """Properties of the pyro payload attached."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        payload = data.get("payload")
        if payload is None:
            raise ValueError("payload field is missing")
        frame = data.get("frame")
        if frame is None:
            raise ValueError("frame field is missing")

        return cls(payload=PyroPayload(**payload), frame=int(frame))


@dataclass
class PyroMarkers:
    """Pyro marker list for a single drone.

    We assume that each pyro channel contains only a single pyro event."""

    markers: dict[int, PyroMarker] = field(default_factory=dict)
    """The list of pyro trigger markers, indexed by the pyro channel."""

    @classmethod
    def from_dict(cls, data: dict[int, PyroMarker]):
        """Creates a pyro markers object from its dictionary representation."""
        return cls(markers=data)

    @classmethod
    def from_str(cls, data: str):
        """Creates a pyro markers object from its string representation."""
        return cls(
            markers={
                int(channel): PyroMarker.from_dict(marker)
                for channel, marker in loads(data).items()
            }
            if data
            else {}
        )

    def as_dict(self) -> dict[int, Any]:
        """Returns the pyro trigger event markers stored for a single drone
        as a dictionary."""
        print(self.markers)
        return {
            int(channel): asdict(marker)
            for channel, marker in sorted(self.markers.items())
        }

    def as_str(self) -> str:
        """Returns the JSON string representation of pyro trigger event markers
        stored for a single drone."""
        return dumps(self.as_dict())
