"""Module containing classes representing the real-world location of a show."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ("ShowLocation",)


@dataclass
class ShowLocation:
    """Structured information about the show location in the real world."""

    orientation: float
    """The orientation of the X+ axis of the show coordinate system
    relative to North (towards East), in degrees."""

    latitude: float
    """The latitude of the show origin, in degrees."""

    longitude: float
    """The longitude of the show origin, in degrees."""

    amsl: float | None = None
    """The optional AMSL altitude of the show origin, in meters."""

    @property
    def json(self):
        """Returns the JSON representation of the show location."""
        origin = [int(self.latitude * 1e7), int(self.longitude * 1e7)]
        if self.amsl is not None:
            origin.append(int(self.amsl * 1e3))

        return {
            "origin": origin,
            "orientation": round(self.orientation, ndigits=3),
        }
