"""Unit tests for blend_in_place_many and BlendMode."""

import numpy as np
import pytest
from numpy import float32
from numpy.testing import assert_allclose, assert_array_equal
from sbstudio.math.colors import BlendMode, blend_in_place


class TestBlendMode:
    def test_description(self):
        assert BlendMode.NORMAL.description == "Normal"
        assert BlendMode.MULTIPLY.description == "Multiply"
        assert BlendMode.SCREEN.description == "Screen"


def _expected_normal(src, dst):
    alpha_s = src[:, 3]
    alpha_d = dst[:, 3]
    alpha_o = np.where(alpha_d >= 1, 1.0, 1.0 - (1.0 - alpha_s) * (1.0 - alpha_d))
    a = np.where(alpha_d >= 1, alpha_s, alpha_s / alpha_o)[:, None]
    rgb = a * src[:, :3] + (1.0 - a) * dst[:, :3]
    return np.column_stack([rgb, alpha_o])


class TestBlendInPlaceMany:
    def test_opaque_normal_overwrites(self):
        src = np.array([[0.8, 0.5, 0.2, 1.0]], dtype=float32)
        dst = np.array([[0.1, 0.3, 0.6, 1.0]], dtype=float32)
        blend_in_place(src, dst, BlendMode.NORMAL)
        assert_array_equal(dst, src)

    def test_many_opaque_normal_matches_formula(self):
        rng = np.random.default_rng(42)
        src = rng.uniform(0, 1, (20, 4)).astype(float32)
        src[:, 3] = 1.0
        dst = rng.uniform(0, 1, (20, 4)).astype(float32)
        expected = src.copy()
        blend_in_place(src, dst, BlendMode.NORMAL)
        assert_allclose(dst, expected, atol=1e-6)

    @pytest.mark.parametrize("mode", BlendMode)
    def test_all_modes_opaque(self, mode):
        src = np.array([[0.8, 0.3, 0.6, 1.0]], dtype=float32)
        dst = np.array([[0.2, 0.7, 0.4, 1.0]], dtype=float32)
        copy = dst.copy()
        blend_in_place(src, copy, mode)
        assert copy.dtype == float32
        assert copy.shape == (1, 4)

    @pytest.mark.parametrize("mode", BlendMode)
    def test_all_modes_semi_transparent(self, mode):
        src = np.array([[0.8, 0.3, 0.6, 0.4]], dtype=float32)
        dst = np.array([[0.2, 0.7, 0.4, 0.7]], dtype=float32)
        copy = dst.copy()
        blend_in_place(src, copy, mode)
        assert copy.dtype == float32
        assert copy.shape == (1, 4)

    def test_alpha_zero_returns_early(self):
        src = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float32)
        dst = np.array([[0.2, 0.4, 0.6, 1.0]], dtype=float32)
        expected = dst.copy()
        blend_in_place(src, dst, BlendMode.NORMAL)
        assert_array_equal(dst, expected)

    def test_all_transparent_returns_early(self):
        src = np.zeros((5, 4), dtype=float32)
        dst = np.ones((5, 4), dtype=float32)
        expected = dst.copy()
        blend_in_place(src, dst, BlendMode.NORMAL)
        assert_array_equal(dst, expected)

    def test_source_not_modified(self):
        src = np.array([[1.0, 0.0, 0.0, 0.5]], dtype=float32)
        dst = np.array([[0.0, 1.0, 0.0, 1.0]], dtype=float32)
        original = src.copy()
        blend_in_place(src, dst, BlendMode.MULTIPLY)
        assert_array_equal(src, original)

    def test_mixed_transparency_normal(self):
        src = np.array(
            [
                [1.0, 0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0, 1.0],
                [1.0, 0.0, 0.0, 0.5],
            ],
            dtype=float32,
        )
        dst = np.array(
            [
                [0.0, 1.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 1.0],
            ],
            dtype=float32,
        )
        expected = _expected_normal(src, dst)
        blend_in_place(src, dst, BlendMode.NORMAL)
        assert_allclose(dst, expected, atol=1e-6)

    def test_output_bounds(self):
        rng = np.random.default_rng(7)
        src = rng.uniform(0, 1, (100, 4)).astype(float32)
        dst = rng.uniform(0, 1, (100, 4)).astype(float32)
        for mode in BlendMode:
            copy = dst.copy()
            blend_in_place(src, copy, mode)
            assert copy.min() >= 0
            assert copy.max() <= 1 + 1e-6

    def test_single_row(self):
        src = np.array([[0.8, 0.3, 0.6, 0.5]], dtype=float32)
        dst = np.array([[0.2, 0.7, 0.4, 0.8]], dtype=float32)
        alpha_s, alpha_d = 0.5, 0.8
        alpha_o = 1.0 - (1.0 - alpha_s) * (1.0 - alpha_d)
        a = alpha_s / alpha_o
        expected_rgb = a * np.array([0.8, 0.3, 0.6]) + (1 - a) * np.array(
            [0.2, 0.7, 0.4]
        )
        expected = np.array(
            [[expected_rgb[0], expected_rgb[1], expected_rgb[2], alpha_o]],
            dtype=float32,
        )
        blend_in_place(src, dst, BlendMode.NORMAL)
        assert_allclose(dst, expected, atol=1e-6)

    def test_large_random_produces_valid_bounds(self):
        rng = np.random.default_rng(123)
        src = rng.uniform(0, 1, (500, 4)).astype(float32)
        dst = rng.uniform(0, 1, (500, 4)).astype(float32)
        for mode in BlendMode:
            copy = dst.copy()
            blend_in_place(src, copy, mode)
            assert copy.min() >= 0
            assert copy.max() <= 1 + 1e-6
