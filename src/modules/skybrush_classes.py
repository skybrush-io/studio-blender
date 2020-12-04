"""This file contains classes and functions for animation softwares to
easily implement drone show exporter plugins for Skybrush."""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from enum import Enum
from gzip import compress
from json import JSONEncoder, loads
from natsort import natsorted
from operator import attrgetter
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory
from typing import List, Dict, Union
from urllib.request import urlopen, Request

from skybrush_utils import create_path_and_open, simplify_path

#############################################################################
# list of public classes from this file

__all__ = [
    "Color4D",
    "Point3D",
    "Point4D",
    "PointCloud",
    "Trajectory",
    "LightCode",
    "SkybrushMatcher",
    "SkybrushExporter",
]


#############################################################################
# configure logger

import logging

log = logging.getLogger(__name__)


#############################################################################
# helper classes and functions to be used locally


def _simplify_color_distance_func(keypoints, start, end):
    """Distance function for LightCode.simplify()"""
    timespan = end.t - start.t

    result = []

    for point in keypoints:
        ratio = (point.t - start.t) / timespan if timespan > 0 else 0.5
        interp = (
            start.r + ratio * (end.r - start.r),
            start.g + ratio * (end.g - start.g),
            start.b + ratio * (end.b - start.b),
        )

        diff = max(
            abs(interp[0] - point.r),
            abs(interp[1] - point.g),
            abs(interp[2] - point.b),
        )
        result.append(diff)

    return result


class SkybrushJSONFormat(Enum):
    """Enum class defining the different JSON formats of Skybrush."""

    # the standard raw Skybrush JSON format used by skybrush converter
    RAW = 0

    # the online Skybrush JSON format to be sent as a http request
    ONLINE = 1


class SkybrushOperatorBase(metaclass=ABCMeta):
    """Meta class for Skybrush operations that animation software plugins
    shall use together with Skybrush Studio installed locally or
    through the online Skybrush Studio Server.

    """

    @abstractmethod
    def as_dict(self, format: SkybrushJSONFormat, ndigits: int = 3) -> dict:
        """Create a Skybrush-compatible dictionary representation of self.

        Parameters:
            format: the format of the output
            ndigits: round floats to this precision

        Return:
            dictionary representation of self
        """
        ...

    def as_json(self, format: SkybrushJSONFormat, ndigits: int = 3) -> str:
        """Create a Skybrush-compatible JSON representation of self.

        Parameters:
            format: the format of the JSON output
            ndigits: number of digits for floats in the JSON output

        Return:
            JSON string representation of self
        """
        if format == SkybrushJSONFormat.RAW:
            encoder = JSONEncoder(indent=2)
        elif format == SkybrushJSONFormat.ONLINE:
            encoder = JSONEncoder(separators=(",", ":"))
        else:
            raise NotImplementedError("Unknown Skybrush JSON format")

        return encoder.encode(self.as_dict(format=format, ndigits=ndigits))

    def to_json(
        self,
        output: Path,
        format: SkybrushJSONFormat,
        ndigits: int = 3,
    ) -> None:
        """Write a Skybrush-compatible JSON representation of the drone show
        stored in self to the given output file.

        Parameters:
            output: the file where the json content should be written
            format: the format of the JSON output
            ndigits: number of digits for floats in the JSON output

        """

        with create_path_and_open(output, "w") as f:
            f.write(self.as_json(format=format, ndigits=ndigits))

    def _ask_skybrush_studio_server(
        self, operation: str, output: Path = None
    ) -> Union[str, None]:
        """Call Skybrush Studio Server at https://studio.skybrush.io to
        perform the required operation on self.

        Parameters:
            operation: the name of the operation to perform
            output: the output path where results should be written

        Return:
            the server's response if output is None, None otherwise.
        """

        # create compressed message content
        data = compress(self.as_json(format=SkybrushJSONFormat.ONLINE).encode("utf-8"))
        headers = {
            "Content-Type": "application/json",
            "Content-Encoding": "gzip",
            "Accept": "application/octet-stream",
        }
        # create request
        url = fr"https://studio.skybrush.io/api/v1/operations/{operation}"
        req = Request(url, data=data, headers=headers, method="POST")
        # send it and wait for response
        log.info("sending http POST request to studio.skybrush.io")
        with urlopen(req) as response:
            # error checks
            status_code = response.getcode()
            info = response.info()
            content_type = info.get_content_type()
            if status_code != 200 or content_type not in [
                "application/octet-stream",
                "application/json",
            ]:
                log.error(f"error in response: status_code={status_code}, info={info}")
                return None
            # return response as a string
            if output is None:
                log.info("response received, returning as a string")
                data = response.read()
                if content_type == "application/octet-stream":
                    data = data.decode("utf-8")
                return data
            # or write it to a file
            else:
                log.info("response received, writing to file")
                mode = "wb" if content_type == "application/octet-stream" else "w"
                with create_path_and_open(output, mode) as f:
                    copyfileobj(response, f)
                return None

        return None


#############################################################################
# handy classes to be used by animation software plugins


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


@dataclass
class Point3D:
    """Simplest representation of a 3D point in space."""

    # x coordinate in [m]
    x: float

    # y coordinate in [m]
    y: float

    # z coordinate in [m]
    z: float

    def at_time(self, t: float) -> Point4D:
        """Returns a Point4D copy of this point such that the copy is placed
        at the given number of seconds on the time axis.

        Parameters:
            t: the number of seconds where the new point should be placed
                on the time axis
        Returns:
            Point4D: the constructed 4D point
        """
        return Point4D(t=t, x=self.x, y=self.y, z=self.z)


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

    def as_3d(self) -> Point3D:
        """Returns a Point3D instance that is at the same coordinates as this
        instance.

        Returns:
            a Point3D instance that is at the same coordinates as this
                instance
        """
        return Point3D(x=self.x, y=self.y, z=self.z)


class PointCloud:
    """Simplest representation of a list/group/cloud of Point3D points."""

    def __init__(self, points: List[Union[Point3D, Point4D]] = []):
        self._points = [Point3D(x=p.x, y=p.y, z=p.z) for p in points]

    def __getitem__(self, item):
        return self._points[item]

    def append(self, point: Union[Point3D, Point4D]) -> None:
        """Add a point to the end of the point cloud."""
        self._points.append(Point3D(x=point.x, y=point.y, z=point.z))

    def as_list(self, ndigits: int = 3):
        """Create a Skybrush-compatible list representation of self.

        Parameters:
            ndigits: round floats to this precision

        Return:
            list representation of self to be converted to JSON later

        """
        return [
            [
                round(point.x, ndigits=ndigits),
                round(point.y, ndigits=ndigits),
                round(point.z, ndigits=ndigits),
            ]
            for point in self._points
        ]

    @property
    def count(self):
        """Return the number of points in self."""
        return len(self._points)


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
            ndigits: round floats to this precision

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
            ndigits: round floats to this precision

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

    def simplify(self) -> LightCode:
        """Simplifies the light code by removing unnecessary keypoints
        from it.

        Return:
            LightCode class with the simplified light code.

        """
        new_items = simplify_path(
            list(self.colors), eps=4, distance_func=_simplify_color_distance_func
        )

        return LightCode(new_items)


#############################################################################
# the main skybrush classes to be used by animation software plugins


class SkybrushExporter(SkybrushOperatorBase):
    """Class for exporting drone show data into Skybrush-compatible formats."""

    def __init__(
        self,
        show_title: str,
        trajectories: Dict[str, Trajectory],
        lights: Dict[str, LightCode],
    ):
        """Class initialization.

        Parameters:
            show_title: arbitrary show title
            trajectories: dictionary of trajectories indexed by drone names
            lights: dictionary of light programs indexed by drone names


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
            ndigits: round floats to this precision

        Return:
            dictionary representation of drone data
        """
        return {
            "type": "generic",
            "settings": {
                "name": name,
                "lights": self._lights[name].as_dict(ndigits=ndigits),
                "trajectory": self._trajectories[name].as_dict(ndigits=ndigits),
            },
        }

    def as_dict(self, format: SkybrushJSONFormat, ndigits: int = 3) -> dict:
        """Create a Skybrush-compatible dictionary representation of the whole
        drone show stored in self.

        Parameters:
            format: the format of the output
            ndigits: round floats to this precision

        Return:
            dictionary representation of self
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

    def to_skyc(self, output: Path) -> None:
        """Write a Skybrush Compiled Format (.skyc) representation of the
        drone show stored in self to the given output file.

        Parameters:
            output: the filename where the output content will be written

        """

        try:
            from skybrush.io.base.importer import find_importer_function, ImportContext
            from skybrush.io.base.renderer import find_renderer_function, RenderContext

            is_skybrush_installed = True
        except ImportError:
            is_skybrush_installed = False

        # temporary hack to see intermediate results
        # self.to_json(r"d:\download\temp.json", format=SkybrushJSONFormat.RAW)
        # return

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
            # if Skybrush Studio is not present locally, try to convert online
            self._ask_skybrush_studio_server("render", output)


class SkybrushMatcher(SkybrushOperatorBase):
    """Class for creating an optimal trajectory mapping between two point clouds."""

    def __init__(
        self,
        source: PointCloud,
        target: PointCloud,
    ):
        """Class initialization.

        Parameters:
            source: the original point cloud where drones should start from
            target: the target point cloud where drones should arrive

        """
        if source.count < target.count:
            raise ValueError(
                f"Source point cloud ({source.count}) must be at least as large as target point cloud ({target.count})"
            )
        self._source = source
        self._target = target

    def as_dict(self, format: SkybrushJSONFormat, ndigits: int = 3):
        """Create a Skybrush-compatible dictionary representation of self.

        Parameters:
            format: the format of the output
            ndigits: round floats to this precision

        Return:
            dictionary representation of self
        """

        data = {
            "source": self._source.as_list(ndigits=ndigits),
            "target": self._target.as_list(ndigits=ndigits),
            "version": 1,
        }

        if format == SkybrushJSONFormat.RAW:
            return data
        elif format == SkybrushJSONFormat.ONLINE:
            return data
        else:
            raise NotImplementedError("Unknown Skybrush JSON format")

    def match(self) -> List[int]:
        """Get the optimal mapping between self's source and target point clouds.

        Return:
            the list of indices of the source point cloud elements in the order
            they are matched with the points in the target point cloud,
            i.e.: from[matching[i]] -> to[i] is the ith assignment, where
            matching[i] can be an integer or None if the ith element of the
            target point cloud is not matched to any point from the source.

        """

        try:
            from skybrush.algorithms.matching import match_pointclouds
            from skybrush.geometry.position import Pos3D

            is_skybrush_installed = True
        except ImportError:
            is_skybrush_installed = False

        if is_skybrush_installed:
            # convert point clouds to skybrush inner format
            source = [Pos3D(x=x, y=y, z=z) for x, y, z in self._source]
            target = [Pos3D(x=x, y=y, z=z) for x, y, z in self._target]
            # call skybrush matching algorithm with default params
            mapping_src = match_pointclouds(source, target, partial=True)
            # invert the mapping
            mapping = [None] * self._target.count
            for i_from, i_to in enumerate(mapping_src):
                if i_to >= 0:
                    mapping[i_to] = i_from

            return mapping

        else:
            # if Skybrush Studio is not present locally, try to convert online
            json_data = self._ask_skybrush_studio_server("match-points", None)
            data = loads(json_data)

            return data["mapping"]
