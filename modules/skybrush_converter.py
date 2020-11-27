"""This file contains classes and functions for animation softwares to
easily implement drone show exporter plugins for Skybrush."""

from dataclasses import dataclass
from enum import Enum
from json import JSONEncoder
from natsort import natsorted
from operator import attrgetter
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory
from typing import List, Dict
from urllib.request import urlopen, Request


#############################################################################
# list of public classes from this file

__all__ = ["Point4D", "Color4D", "Trajectory", "LightCode", "SkybrushConverter"]


#############################################################################
# configure logger

import logging

log = logging.getLogger(__name__)


#############################################################################
# helper classes to be used by animation software plugins


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

    def as_dict(self, ndigits: int = 3):
        """Create a Skybrush-compatible dictionary representation of self.

        Parameters:
            ndigits - round floats to this precision

        Return:
            dictionary of self to be converted to SJON later

        """
        return {
            "points": [
                [
                    round(point.t, ndigits=ndigits),
                    [
                        round(point.x, ndigits=ndigits),
                        round(point.y, ndigits=ndigits),
                        round(point.z, ndigits=ndigits),
                    ],
                    [],
                ]
                for point in self.points
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

    def as_dict(self, ndigits: int = 3):
        """Create a Skybrush-compatible dictionary representation of self.

        Parameters:
            ndigits - round floats to this precision

        Return:
            dictionary of self to be converted to SJON later

        """
        return {
            "data": [
                [
                    round(color.t, ndigits=ndigits),
                    [
                        round(color.r, ndigits=ndigits),
                        round(color.g, ndigits=ndigits),
                        round(color.b, ndigits=ndigits),
                    ],
                    color.is_fade,
                ]
                for color in self.colors
            ],
            "version": 1,
        }


#############################################################################
# helper functions and classes to be used locally


class SkybrushJSONFormat(Enum):
    """Enum class defining the different JSON formats of Skybrush."""

    # the standard raw Skybrush JSON format used by skybrush converter
    RAW = 0

    # the online Skybrush JSON format to be sent as a http request
    ONLINE = 1


def create_path_and_open(filename, *args, **kwds):
    """Like open() but also creates the directories leading to the given file
    if they don't exist yet.
    """
    if not isinstance(filename, Path):
        path = Path(filename)
    else:
        path = filename

    path.parent.mkdir(exist_ok=True, parents=True)
    return open(str(path), *args, **kwds)


#############################################################################
# the main skybrush converter class to be used by animation software plugins


class SkybrushConverter:
    """Class for converting drone show data to Skybrush-compatible formats."""

    def __init__(
        self,
        show_title: str,
        trajectories: Dict[str, Trajectory],
        lights: Dict[str, LightCode],
        ndigits: int = 3,
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

    def _drone_data_as_dict(self, name: str, ndigits: int = 3) -> dict:
        """Create a Skybrush-compatible dictionary representation of all data
        related to a single drone stored in self.

        Parameters:
            name: the name of the given drone in self database
            ndigits - round floats to this precision

        Return:
            dict representation of drone data
        """
        return {
            "type": "generic",
            "settings": {
                "name": name,
                "lights": self._lights[name].as_dict(ndigits=ndigits),
                "trajectory": self._trajectories[name].as_dict(ndigits=ndigits),
            },
        }

    def as_dict(self, format: SkybrushJSONFormat, ndigits: int = 3):
        """Create a Skybrush-compatible dictionary representation of the whole
        drone show stored in self.

        Parameters:
            format: the format of the output
            ndigits - round floats to this precision

        Return:
            dict representation of self
        """

        data = {
            "version": 1,
            "settings": {},
            "swarm": {
                "drones": [
                    self._drone_data_as_dict(name, ndigits=ndigits)
                    for name in natsorted(self._trajectories.keys())
                ]
            },
            "meta": {"title": self._show_title},
        }

        if format == SkybrushJSONFormat.RAW:
            return data
        elif format == SkybrushJSONFormat.ONLINE:
            return {
                "input": {"format": "json", "data": data},
                "output": {"format": "skyc"},
            }
        else:
            raise NotImplementedError("Unknown Skybrush JSON format")

    def as_json(
        self, format: SkybrushJSONFormat, indent: int = 2, ndigits: int = 3
    ) -> str:
        """Create a Skybrush-compatible JSON representation of the drone show
        stored in self.

        Parameters:
            format: the format of the JSON output
            indent: indentation level in the JSON output
            ndigits: number of digits for floats in the JSON output

        Return:
            JSON string representation of self
        """

        encoder = JSONEncoder(indent=indent)
        return encoder.encode(self.as_dict(format=format, ndigits=ndigits))

    def to_json(
        self,
        output: Path,
        format: SkybrushJSONFormat,
        indent: int = 2,
        ndigits: int = 3,
    ) -> None:
        """Write a Skybrush-compatible JSON representation of the drone show
        stored in self to the given output file.

        Parameters:
            output: the file where the json content should be written
            format: the format of the JSON output
            indent: indentation level in the JSON output
            ndigits: number of digits for floats in the JSON output

        """

        with create_path_and_open(output, "w") as f:
            f.write(self.as_json(format=format, indent=indent, ndigits=ndigits))

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

        # TODO: this is here for debug reasons to test the online version
        is_skybrush_installed = False

        if is_skybrush_installed:
            with TemporaryDirectory() as work_dir:
                # first create a temporary JSON representation
                json_output = Path(work_dir) / Path("show.json")
                self.to_json(json_output, format=SkybrushJSONFormat.RAW)
                # then send it to skybrush to convert it to .skyc
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
            # online tool available at https://studio.skybrush.io

            # create message content
            data = self.as_json(format=SkybrushJSONFormat.ONLINE).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/octet-stream",
            }
            # create request
            url = r"https://studio.skybrush.io/api/v1/operations/render"
            req = Request(url, data=data, headers=headers, method="POST")
            # send it and wait for response
            log.info("sending http POST request to studio.skybrush.io")
            with urlopen(req) as response:
                # error checks
                status_code = response.getcode()
                info = response.info()
                content_type = info.get_content_type()
                if status_code != 200 or content_type != "application/octet-stream":
                    log.error(
                        f"error in response: status_code={status_code}, info={info}"
                    )
                    return
                # write response to file
                log.info("writing response to file")
                with create_path_and_open(output, "wb") as f:
                    copyfileobj(response, f)
