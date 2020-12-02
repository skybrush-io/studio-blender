"""Unit tests of the SkybrushMorpher class."""

import os
import sys

module_path = os.path.join(
    os.path.dirname(sys.modules[__name__].__file__), "..", "modules"
)
if module_path not in sys.path:
    sys.path.append(module_path)

from skybrush_classes import SkybrushMatcher, Point3D, PointCloud


def main():
    source = PointCloud([Point3D(0, 0, 0), Point3D(1, 2, 3), Point3D(0, 10, 20)])
    target = PointCloud([Point3D(0, 2, 0), Point3D(0, 10, 2), Point3D(1, 0, 3)])

    mapping = SkybrushMatcher(source=source, target=target).match()
    for i_to, i_from in enumerate(mapping):
        from_str = "None" if i_from is None else str(source[i_from])
        print(f"{from_str} -> {target[i_to]}")