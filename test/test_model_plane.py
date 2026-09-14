"""Unit tests for the Plane class."""

import numpy as np
import pytest
from sbstudio.model.plane import Plane


class TestConstruction:
    def test_from_normal_and_point_basic(self):
        plane = Plane.from_normal_and_point((0, 0, 1), (0, 0, 5))
        assert all(plane.normal == (0, 0, 1))
        assert plane.offset == 5

    def test_from_normal_and_point_negative_offset(self):
        plane = Plane.from_normal_and_point((0, 0, 1), (0, 0, -3))
        assert all(plane.normal == (0, 0, 1))
        assert plane.offset == -3

    def test_from_normal_and_point_origin(self):
        plane = Plane.from_normal_and_point((1, 0, 0), (0, 0, 0))
        assert plane.offset == 0

    def test_from_normal_and_point_non_unit_normal(self):
        plane = Plane.from_normal_and_point((2, 0, 0), (1, 0, 0))
        assert all(plane.normal == (2, 0, 0))
        assert plane.offset == 2

    def test_from_points_xy_plane(self):
        plane = Plane.from_points((0, 0, 0), (1, 0, 0), (0, 1, 0))
        assert all(plane.normal == (0, 0, 1))
        assert plane.offset == 0

    def test_from_points_yz_plane(self):
        plane = Plane.from_points((0, 0, 0), (0, 1, 0), (0, 0, 1))
        assert plane.normal[0] != 0
        assert plane.normal[1] == 0
        assert plane.normal[2] == 0
        assert plane.offset == 0

    def test_from_points_xz_plane(self):
        plane = Plane.from_points((0, 0, 0), (1, 0, 0), (0, 0, 1))
        assert plane.normal[0] == 0
        assert plane.normal[1] != 0
        assert plane.normal[2] == 0
        assert plane.offset == 0

    def test_from_points_with_offset(self):
        plane = Plane.from_points((0, 0, 1), (1, 0, 1), (0, 1, 1))
        assert all(plane.normal == (0, 0, 1))
        assert plane.offset == 1

    def test_from_points_collinear_raises(self):
        with pytest.raises(RuntimeError, match="collinear"):
            Plane.from_points((0, 0, 0), (1, 0, 0), (2, 0, 0))

    def test_from_points_collinear_duplicate_points_raises(self):
        with pytest.raises(RuntimeError, match="collinear"):
            Plane.from_points((1, 1, 1), (2, 2, 2), (1, 1, 1))


class TestIsFront:
    def test_point_in_front(self):
        plane = Plane.from_normal_and_point((0, 0, 1), (0, 0, 0))
        assert plane.is_front((0, 0, 1))

    def test_point_behind(self):
        plane = Plane.from_normal_and_point((0, 0, 1), (0, 0, 0))
        assert not plane.is_front((0, 0, -1))

    def test_point_on_plane_is_front(self):
        plane = Plane.from_normal_and_point((0, 0, 1), (0, 0, 5))
        assert plane.is_front((0, 0, 5))

    def test_point_on_plane_is_front_origin(self):
        plane = Plane.from_normal_and_point((1, 0, 0), (0, 0, 0))
        assert plane.is_front((0, 0, 0))

    def test_diagonal_plane(self):
        plane = Plane.from_points((0, 0, 0), (1, 1, 0), (1, 0, 1))
        assert plane.is_front((1, 1, 1))
        assert not plane.is_front((-1, -1, -1))

    def test_arbitrary_plane(self):
        plane = Plane.from_normal_and_point((1, 2, 3), (1, 1, 1))
        assert plane.is_front((2, 2, 2))
        assert not plane.is_front((0, 0, 0))


class TestIsFrontMany:
    def test_basic(self):
        plane = Plane.from_normal_and_point((0, 0, 1), (0, 0, 0))
        points = np.array([[0, 0, 1], [0, 0, -1], [0, 0, 0]], dtype=np.float64)
        result = np.zeros(len(points), dtype=np.bool_)
        plane.is_front_many(points, result)
        assert list(result) == [True, False, True]

    def test_returns_bool_array(self):
        plane = Plane.from_normal_and_point((1, 0, 0), (5, 0, 0))
        points = np.array([[5, 0, 0], [6, 0, 0], [4, 0, 0]], dtype=np.float64)
        result = np.zeros(len(points), dtype=np.bool_)
        plane.is_front_many(points, result)
        assert list(result) == [True, True, False]

    def test_diagonal_plane(self):
        plane = Plane.from_points((0, 0, 0), (1, 1, 0), (1, 0, 1))
        points = np.array([[1, 1, 1], [-1, -1, -1], [0, 0, 0]], dtype=np.float64)
        result = np.zeros(len(points), dtype=np.bool_)
        plane.is_front_many(points, result)
        assert list(result) == [True, False, True]

    def test_large_input(self):
        plane = Plane.from_normal_and_point((1, 0, 0), (0, 0, 0))
        n = 1000
        points = np.random.default_rng(42).uniform(-10, 10, (n, 3)).astype(np.float64)
        result = np.zeros(len(points), dtype=np.bool_)
        plane.is_front_many(points, result)

    def test_matches_is_front(self):
        plane = Plane.from_normal_and_point((2, 3, 5), (1, 1, 1))
        points = np.array(
            [[1, 2, 3], [-1, 0, 2], [5, -3, 1], [0, 0, 0]], dtype=np.float64
        )
        expected = np.array([plane.is_front(tuple(p)) for p in points], dtype=np.bool_)
        result = np.zeros(len(points), dtype=np.bool_)
        plane.is_front_many(points, result)
        assert list(result) == list(expected)


class TestDataclassBehavior:
    def test_frozen_immutable(self):
        plane = Plane.from_normal_and_point((0, 0, 1), (0, 0, 0))
        with pytest.raises(AttributeError):
            plane.normal = (1, 0, 0)

    def test_equality(self):
        a = Plane.from_normal_and_point((0, 0, 1), (0, 0, 5))
        b = Plane.from_normal_and_point((0, 0, 1), (0, 0, 5))
        assert a == b

    def test_inequality(self):
        a = Plane.from_normal_and_point((0, 0, 1), (0, 0, 5))
        b = Plane.from_normal_and_point((1, 0, 0), (5, 0, 0))
        assert a != b

    def test_repr(self):
        plane = Plane.from_normal_and_offset(normal=(0, 0, 1), offset=5.0)
        r = repr(plane)
        assert "Plane" in r
        assert "0.0" in r
        assert "1.0" in r
        assert "5.0" in r

    def test_direct_construction(self):
        plane = Plane.from_normal_and_offset(normal=(1.0, 2.0, 3.0), offset=4.0)
        assert all(plane.normal == (1.0, 2.0, 3.0))
        assert plane.offset == 4.0


class TestFromPointsToIsFront:
    def test_plane_from_points_front_and_back(self):
        plane = Plane.from_points((0, 0, 0), (1, 0, 0), (0, 1, 0))
        assert plane.is_front((0, 0, 1))
        assert not plane.is_front((0, 0, -1))

    def test_plane_from_points_on_plane(self):
        plane = Plane.from_points((0, 0, 0), (1, 0, 0), (0, 1, 0))
        assert plane.is_front((0.5, 0.5, 0))
        assert plane.is_front((2, 3, 0))
