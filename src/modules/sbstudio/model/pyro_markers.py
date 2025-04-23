from dataclasses import dataclass, field
from json import dumps, loads

from typing import Any

__all__ = ("PyroMarkers",)


@dataclass
class PyroMarker:
    """Descriptor of a single pyro trigger event
    on a specific drone's specific pyro channel.

    So far we assume that one channel can be used only once for pyro triggering."""

    name: str
    """Unique descriptor of the pyro effect to trigger, in VDL format."""

    frame: int
    """The frame number of the trigger event."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        name = data.get("name")
        if name is None:
            raise ValueError("name field is missing")
        frame = data.get("frame")
        if frame is None:
            raise ValueError("frame field is missing")

        return cls(name=str(name).strip(), frame=int(frame))

    def as_dict(self):
        """Returns the pyro trigger event marker as a dictionary."""
        return {"name": self.name, "frame": self.frame}


@dataclass
class PyroMarkers:
    """Pyro marker list for a single drone."""

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
            int(channel): marker.as_dict()
            for channel, marker in sorted(self.markers.items())
        }

    def as_str(self) -> str:
        """Returns the JSON string representation of pyro trigger event markers
        stored for a single drone."""
        return dumps(self.as_dict())
