"""This file contains classes and functions for animation softwares to
easily implement drone show exporter plugins for Skybrush."""

from dataclasses import dataclass
from json import JSONEncoder
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Dict
from operator import attrgetter


@dataclass
class Point4D:
    """Simplest representation of a 4D point in space and time."""

    # time in [s]
    t: float

    # x coordinate in [m]
    x: float

    # y coordinate in [m]
    y: float

    # z coordinate in [m]
    z: float


@dataclass
class Color4D:
    """Simplest representation of a 4D color in RGB space and time."""

    # time in [s]
    t: float

    # red component of the color in the range [0-255]
    r: int

    # green component of the color in the range[0-255]
    g: int

    # blue component of the color in the range[0-255]
    b: int

    # flag to specify whether we should fade here from the previous keypoint (True)
    # or maintain previous color until this moment and change here abruptly (False)
    is_fade: bool = True


class Trajectory:
    """Simplest representation of a causal trajectory in space and time.

    Positions between given Point4D elements are assumed to be
    linearly interpolated both in space and time.

    """

    def __init__(self, points: List[Point4D] = []):
        self.points = sorted(points, key=attrgetter("t"))

    def append(self, point: Point4D) -> None:
        """Add a point to the end of the trajectory."""
        if self.points and self.points[-1].t >= point.t:
            raise ValueError("New point must come after existing trajectory in time")
        self.points.append(point)

    def as_dict(self):
        """Create a Skybrush-compatible dictionary representation of self."""
        return {
            "points": [
                [point.t, [point.x, point.y, point.z], []] for point in self.points
            ],
            "version": 1,
        }


class LightCode:
    """Simplest representation of a causal light code in space and time.

    The color between given points is linearly interpolated or kept constant
    from past according to the is_fade property of each Color4D element.

    """

    def __init__(self, colors: List[Color4D] = []):
        self.colors = sorted(colors, key=attrgetter("t"))

    def append(self, color: Color4D) -> None:
        """Add a color to the end of the light code."""
        if self.colors and self.colors[-1].t > color.t:
            raise ValueError("New color must come after existing light code in time")
        self.colors.append(color)

    def as_dict(self):
        """Create a Skybrush-compatible dictionary representation of self."""
        return {
            "data": [
                [color.t, [color.r, color.g, color.b], color.is_fade]
                for color in self.colors
            ],
            "version": 1,
        }


def _create_path_and_open(filename, *args, **kwds):
    """Like open() but also creates the directories leading to the given file
    if they don't exist yet.
    """
    if not isinstance(filename, Path):
        path = Path(filename)
    else:
        path = filename

    path.parent.mkdir(exist_ok=True, parents=True)
    return open(str(path), *args, **kwds)


class _PrettyFloat:
    """Placeholder object for floating-point numbers that can be used in a
    JSON serialization to ensure that they are printed nicely without
    rounding errors.
    """

    def __init__(self, value):
        self._value = value

    @classmethod
    def prettify(cls, obj, digits: int = None):
        """Recursively traverses a JSON object and replaces floats with
        PrettyFloat_ instances that can then be serialized nicely into JSON
        without rounding errors.
        """
        if isinstance(obj, float):
            if digits is not None:
                obj = round(obj, digits)
            return cls(obj)
        elif isinstance(obj, dict):
            return {k: cls.prettify(v, digits=digits) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [cls.prettify(x, digits=digits) for x in obj]
        else:
            return obj

    @classmethod
    def encoder(cls, obj):
        if isinstance(obj, cls):
            return float(format(obj._value, ".17f"))
        else:
            raise TypeError("{0!r} cannot be serialized in JSON", type(obj))


class SkybrushConverter:
    """Class for converting drone show data to Skybrush-compatible formats."""

    def __init__(
        self,
        show_title: str,
        trajectories: Dict[str, Trajectory],
        lights: Dict[str, LightCode],
    ):
        """Class initialization.

        Parameters:
            show_title - arbitrary show title
            trajectories - dictionary of trajectories indexed by drone names
            lights - dictionary of light programs indexed by drone names

        Note: drone names must match in trajectories and lights

        """
        self._show_title = show_title
        if sorted(trajectories.keys()) != sorted(lights.keys()):
            raise ValueError(
                "Trajectories and lights must contain equal number of items, one for each drone."
            )
        self._trajectories = trajectories
        self._lights = lights

    def _drone_data_as_dict(self, name: str) -> dict:
        """Create a Skybrush-compatible dictionary representation of all data
        related to a single drone stored in self.

        Parameters:
            name: the name of the given drone in self database

        Return:
            dict representation of drone data
        """
        return {
            "type": "generic",
            "settings": {
                "name": name,
                "lights": self._lights[name].as_dict(),
                "trajectory": self._trajectories[name].as_dict(),
            },
        }

    def as_dict(self):
        """Create a Skybrush-compatible dictionary representation of the whole
        drone show stored in self."""

        return {
            "version": 1,
            "settings": {},
            "swarm": {
                "drones": [
                    self._drone_data_as_dict(name)
                    for name in sorted(self._trajectories.keys())
                ]
            },
            "meta": {"title": self._show_title},
        }

    def as_json(self, indent: int = 2, digits: int = 3) -> str:
        """Create a Skybrush-compatible JSON representation of the drone show
        stored in self.

        Parameters:
            indent: indentation level in the JSON output
            digits: number of digits for floats in the JSON output

        Return:
            JSON string representation of self
        """

        encoder = JSONEncoder(indent=indent, default=_PrettyFloat.encoder)
        return encoder.encode(_PrettyFloat.prettify(self.as_dict(), digits=digits))

    def to_json(self, output: Path, indent: int = 2, digits: int = 3) -> None:
        """Write a Skybrush-compatible JSON representation of the drone show
        stored in self to the given output file.

        Parameters:
            output: the file where the json content should be written
            indent: indentation level in the JSON output
            digits: number of digits for floats in the JSON output

        """

        with _create_path_and_open(output, "w") as f:
            f.write(self.as_json(indent=indent, digits=digits))

    def to_skyc(self, output: Path) -> None:
        """Write a Skybrush Compiled Format (.skyc) representation of the
        drone show stored in self to the given output file.

        Parameters:
            output - the filename where the output content will be written

        """

        try:
            from skybrush.io.base.importer import find_importer_function, ImportContext
            from skybrush.io.base.renderer import find_renderer_function, RenderContext

            is_skybrush_installed = True
        except ImportError:
            is_skybrush_installed = False

        with TemporaryDirectory() as work_dir:
            # first create a temporary .json representation
            json_output = Path(work_dir) / Path("show.json")
            self.to_json(json_output)

            # then render it to .skyc
            if is_skybrush_installed:
                importer = find_importer_function("skybrush.io.json.importer")
                context = ImportContext()
                parameters = {}
                world = importer([json_output], context, parameters)
                renderer = find_renderer_function("skybrush.io.skyc.renderer")
                context = RenderContext()
                parameters = {"output": output}
                renderer(world, context, parameters)
            else:
                # if Skybrush Studio is not present locally, try to convert with the
                # online tool available at https://skybrush.io
                raise NotImplementedError(
                    "Online Skybrush converter not implemented yet"
                )
