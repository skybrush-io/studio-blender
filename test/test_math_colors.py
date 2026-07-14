"""Unit tests for blend_in_place and BlendMode."""

import numpy as np
import pytest
from numpy import float32
from numpy.testing import assert_allclose, assert_array_equal
from sbstudio.math.colors import BlendMode, blend_in_place


@pytest.fixture
def src() -> np.ndarray:
    return np.array([0.8, 0.5, 0.2, 1.0], dtype=float32)


@pytest.fixture
def dst() -> np.ndarray:
    return np.array([0.1, 0.3, 0.6, 1.0], dtype=float32)


class TestBlendMode:
    def test_description(self):
        assert BlendMode.NORMAL.description == "Normal"
        assert BlendMode.MULTIPLY.description == "Multiply"
        assert BlendMode.SCREEN.description == "Screen"


class TestTransparentSource:
    def test_alpha_zero_returns_early(self):
        source = np.array([1.0, 0.0, 0.0, 0.0], dtype=float32)
        backdrop = np.array([0.2, 0.4, 0.6, 1.0], dtype=float32)
        expected = backdrop.copy()
        blend_in_place(source, backdrop, BlendMode.NORMAL)
        assert_array_equal(backdrop, expected)

    def test_alpha_zero_with_non_normal_mode(self):
        source = np.array([1.0, 0.0, 0.0, 0.0], dtype=float32)
        backdrop = np.array([0.2, 0.4, 0.6, 1.0], dtype=float32)
        expected = backdrop.copy()
        blend_in_place(source, backdrop, BlendMode.MULTIPLY)
        assert_array_equal(backdrop, expected)


class TestOpaqueNormalShortcut:
    def test_opaque_normal_overwrites(self, src, dst):
        blend_in_place(src, dst, BlendMode.NORMAL)
        assert_array_equal(dst, src)

    def test_opaque_normal_alpha_unchanged(self):
        source = np.array([0.3, 0.6, 0.9, 1.0], dtype=float32)
        backdrop = np.array([0.1, 0.2, 0.3, 0.5], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.NORMAL)
        assert_array_equal(backdrop, source)

    def test_source_not_modified(self, src, dst):
        original = src.copy()
        blend_in_place(src, dst, BlendMode.MULTIPLY)
        assert_array_equal(src, original)


class TestAlphaCompositing:
    def test_semi_transparent_over_opaque(self):
        source = np.array([1.0, 0.0, 0.0, 0.5], dtype=float32)
        backdrop = np.array([0.0, 1.0, 0.0, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.NORMAL)
        expected = np.array([0.5, 0.5, 0.0, 1.0], dtype=float32)
        assert_allclose(backdrop, expected, atol=1e-6)

    def test_transparent_over_transparent(self):
        source = np.array([1.0, 0.0, 0.0, 0.3], dtype=float32)
        backdrop = np.array([0.0, 1.0, 0.0, 0.6], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.NORMAL)
        assert backdrop[3] == pytest.approx(1 - (1 - 0.3) * (1 - 0.6))
        assert backdrop[0] > 0
        assert backdrop[1] > 0

    def test_opaque_non_normal_no_shortcut(self):
        source = np.array([1.0, 0.0, 0.0, 1.0], dtype=float32)
        backdrop = np.array([0.0, 1.0, 0.0, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.MULTIPLY)
        assert_allclose(backdrop, [0.0, 0.0, 0.0, 1.0], atol=1e-6)


class TestBlendModes:
    def test_normal(self):
        source = np.array([0.6, 0.3, 0.9, 0.5], dtype=float32)
        backdrop = np.array([0.2, 0.7, 0.1, 0.8], dtype=float32)
        result = backdrop.copy()
        blend_in_place(source, result, BlendMode.NORMAL)
        a, b = 0.5 / (1 - (1 - 0.5) * (1 - 0.8)), 1 - 0.5 / (1 - (1 - 0.5) * (1 - 0.8))
        expected_rgb = [a * s + b * d for s, d in zip(source[:3], backdrop[:3])]
        expected = np.array([*expected_rgb, 1 - (1 - 0.5) * (1 - 0.8)], dtype=float32)
        assert_allclose(result, expected, atol=1e-6)

    def test_multiply(self):
        source = np.array([0.8, 0.5, 0.2, 1.0], dtype=float32)
        backdrop = np.array([0.1, 0.3, 0.6, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.MULTIPLY)
        expected = np.array(
            [
                0.8 * 0.1 * 1.0,
                0.5 * 0.3 * 1.0,
                0.2 * 0.6 * 1.0,
                1.0,
            ],
            dtype=float32,
        )
        assert_allclose(backdrop, expected, atol=1e-6)

    def test_screen(self):
        source = np.array([0.8, 0.5, 0.2, 1.0], dtype=float32)
        backdrop = np.array([0.1, 0.3, 0.6, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.SCREEN)
        expected = np.array(
            [
                1 - (1 - 0.1) * (1 - 0.8),
                1 - (1 - 0.3) * (1 - 0.5),
                1 - (1 - 0.6) * (1 - 0.2),
                1.0,
            ],
            dtype=float32,
        )
        assert_allclose(backdrop, expected, atol=1e-6)

    def test_darken(self):
        source = np.array([0.8, 0.5, 0.2, 1.0], dtype=float32)
        backdrop = np.array([0.1, 0.3, 0.6, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.DARKEN)
        expected = np.array(
            [min(0.1, 0.8), min(0.3, 0.5), min(0.6, 0.2), 1.0], dtype=float32
        )
        assert_allclose(backdrop, expected, atol=1e-6)

    def test_lighten(self):
        source = np.array([0.8, 0.5, 0.2, 1.0], dtype=float32)
        backdrop = np.array([0.1, 0.3, 0.6, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.LIGHTEN)
        expected = np.array(
            [max(0.1, 0.8), max(0.3, 0.5), max(0.6, 0.2), 1.0], dtype=float32
        )
        assert_allclose(backdrop, expected, atol=1e-6)

    def test_overlay_backdrop_ge_05(self):
        source = np.array([0.2, 0.0, 0.0, 1.0], dtype=float32)
        backdrop = np.array([0.7, 0.8, 0.9, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.OVERLAY)
        expected_r = 1 - (2 - 2 * 0.7) * (1 - 0.2)
        expected_g = 1 - (2 - 2 * 0.8) * (1 - 0.0)
        expected_b = 1 - (2 - 2 * 0.9) * (1 - 0.0)
        expected = np.array([expected_r, expected_g, expected_b, 1.0], dtype=float32)
        assert_allclose(backdrop, expected, atol=1e-6)

    def test_overlay_backdrop_lt_05(self):
        source = np.array([0.2, 0.0, 0.0, 1.0], dtype=float32)
        backdrop = np.array([0.3, 0.4, 0.1, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.OVERLAY)
        expected_r = 2 * 0.3 * 0.2
        expected_g = 2 * 0.4 * 0.0
        expected_b = 2 * 0.1 * 0.0
        expected = np.array([expected_r, expected_g, expected_b, 1.0], dtype=float32)
        assert_allclose(backdrop, expected, atol=1e-6)

    def test_overlay_mixed(self):
        source = np.array([0.2, 0.8, 0.0, 1.0], dtype=float32)
        backdrop = np.array([0.3, 0.7, 0.9, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.OVERLAY)
        expected_r = 2 * 0.3 * 0.2  # backdrop=0.3 < 0.5
        expected_g = 1 - (2 - 2 * 0.7) * (1 - 0.8)  # backdrop=0.7 >= 0.5
        expected_b = 1 - (2 - 2 * 0.9) * (1 - 0.0)  # backdrop=0.9 >= 0.5
        expected = np.array([expected_r, expected_g, expected_b, 1.0], dtype=float32)
        assert_allclose(backdrop, expected, atol=1e-6)

    def test_hard_light_source_le_05(self):
        source = np.array([0.4, 0.3, 0.5, 1.0], dtype=float32)
        backdrop = np.array([0.7, 0.2, 0.9, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.HARD_LIGHT)
        expected_r = 0.7 * (2 * 0.4)
        expected_g = 0.2 * (2 * 0.3)
        expected_b = 0.9 * (2 * 0.5)
        expected = np.array([expected_r, expected_g, expected_b, 1.0], dtype=float32)
        assert_allclose(backdrop, expected, atol=1e-6)

    def test_hard_light_source_gt_05(self):
        source = np.array([0.6, 0.7, 0.8, 1.0], dtype=float32)
        backdrop = np.array([0.3, 0.4, 0.5, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.HARD_LIGHT)
        expected_r = 1 - (1 - 0.3) * (2 - 2 * 0.6)
        expected_g = 1 - (1 - 0.4) * (2 - 2 * 0.7)
        expected_b = 1 - (1 - 0.5) * (2 - 2 * 0.8)
        expected = np.array([expected_r, expected_g, expected_b, 1.0], dtype=float32)
        assert_allclose(backdrop, expected, atol=1e-6)

    def test_hard_light_mixed(self):
        source = np.array([0.4, 0.7, 0.5, 1.0], dtype=float32)
        backdrop = np.array([0.7, 0.2, 0.9, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.HARD_LIGHT)
        expected_r = 0.7 * (2 * 0.4)  # source=0.4 <= 0.5
        expected_g = 1 - (1 - 0.2) * (2 - 2 * 0.7)  # source=0.7 > 0.5
        expected_b = 0.9 * (2 * 0.5)  # source=0.5 <= 0.5
        expected = np.array([expected_r, expected_g, expected_b, 1.0], dtype=float32)
        assert_allclose(backdrop, expected, atol=1e-6)

    def test_soft_light_source_le_05(self):
        source = np.array([0.4, 0.3, 0.2, 1.0], dtype=float32)
        backdrop = np.array([0.6, 0.7, 0.5, 1.0], dtype=float32)
        original = backdrop.copy()
        blend_in_place(source, backdrop, BlendMode.SOFT_LIGHT)
        expected = np.array(
            [
                original[i] - (1 - 2 * source[i]) * original[i] * (1 - original[i])
                for i in range(3)
            ]
            + [1.0],
            dtype=float32,
        )
        assert_allclose(backdrop, expected, atol=1e-6)

    def test_soft_light_source_gt_05_backdrop_gt_025(self):
        source = np.array([0.8, 0.9, 0.7, 1.0], dtype=float32)
        backdrop = np.array([0.5, 0.6, 0.3, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.SOFT_LIGHT)
        d = [b**0.5 for b in [0.5, 0.6, 0.3]]
        expected = np.array(
            [
                0.5 + (2 * 0.8 - 1) * (d[0] - 0.5),
                0.6 + (2 * 0.9 - 1) * (d[1] - 0.6),
                0.3 + (2 * 0.7 - 1) * (d[2] - 0.3),
                1.0,
            ],
            dtype=float32,
        )
        assert_allclose(backdrop, expected, atol=1e-6)

    def test_soft_light_source_gt_05_backdrop_le_025(self):
        source = np.array([0.8, 0.9, 0.7, 1.0], dtype=float32)
        backdrop = np.array([0.2, 0.1, 0.25, 1.0], dtype=float32)
        blend_in_place(source, backdrop, BlendMode.SOFT_LIGHT)
        d = [((16 * b - 12) * b + 4) * b for b in [0.2, 0.1, 0.25]]
        expected = np.array(
            [
                0.2 + (2 * 0.8 - 1) * (d[0] - 0.2),
                0.1 + (2 * 0.9 - 1) * (d[1] - 0.1),
                0.25 + (2 * 0.7 - 1) * (d[2] - 0.25),
                1.0,
            ],
            dtype=float32,
        )
        assert_allclose(backdrop, expected, atol=1e-6)


class TestAllModesRoundTrip:
    @pytest.mark.parametrize(
        "mode",
        [
            BlendMode.NORMAL,
            BlendMode.MULTIPLY,
            BlendMode.SCREEN,
            BlendMode.DARKEN,
            BlendMode.LIGHTEN,
            BlendMode.OVERLAY,
            BlendMode.HARD_LIGHT,
            BlendMode.SOFT_LIGHT,
        ],
    )
    def test_all_modes_opaque(self, mode):
        source = np.array([0.8, 0.3, 0.6, 1.0], dtype=float32)
        backdrop = np.array([0.2, 0.7, 0.4, 1.0], dtype=float32)
        result = backdrop.copy()
        blend_in_place(source, result, mode)
        assert result.dtype == float32
        assert result.shape == (4,)
        assert all(0 <= v <= 1 for v in result)

    @pytest.mark.parametrize(
        "mode",
        [
            BlendMode.NORMAL,
            BlendMode.MULTIPLY,
            BlendMode.SCREEN,
            BlendMode.DARKEN,
            BlendMode.LIGHTEN,
            BlendMode.OVERLAY,
            BlendMode.HARD_LIGHT,
            BlendMode.SOFT_LIGHT,
        ],
    )
    def test_all_modes_semi_transparent(self, mode):
        source = np.array([0.8, 0.3, 0.6, 0.4], dtype=float32)
        backdrop = np.array([0.2, 0.7, 0.4, 0.7], dtype=float32)
        result = backdrop.copy()
        blend_in_place(source, result, mode)
        assert result.dtype == float32
        assert result.shape == (4,)
        assert all(0 <= v <= 1 for v in result)


class TestResultInRange:
    def test_all_modes_opaque_produce_valid_rgba(self):
        sources = np.linspace(0, 1, 5)
        backdrops = np.linspace(0, 1, 5)
        for mode in BlendMode:
            for s in sources:
                for d in backdrops:
                    src = np.array([s, s, s, 1.0], dtype=float32)
                    dst = np.array([d, d, d, 1.0], dtype=float32)
                    blend_in_place(src, dst, mode)
                    assert all(0 <= v <= 1 + 1e-6 for v in dst)
