from json import loads
from typing import List

from sbstudio.model.point_cloud import PointCloud

from .base import SkybrushAPIOperationBase

from ..enums import SkybrushJSONFormat

#############################################################################
# list of public classes from this file

__all__ = ("SkybrushMatcher",)


class SkybrushMatcher(SkybrushAPIOperationBase):
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
        """Create a Skybrush-compatible dictionary representation of this
        instance.

        Parameters:
            format: the format of the output
            ndigits: round floats to this precision

        Return:
            dictionary representation of this instance
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

            return data.get("mapping")
