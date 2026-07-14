"""Unit tests for the RandomSequence class."""

from random import Random
from random import seed as set_seed

import numpy as np
import pytest
from sbstudio.math.rng import RandomSequence


class TestConstruction:
    def test_default_max(self):
        seq = RandomSequence(seed=42)
        assert seq.max == 0xFFFFFFFF

    def test_custom_max(self):
        seq = RandomSequence(seed=42, max=100)
        assert seq.max == 100

    def test_is_sequence(self):
        seq = RandomSequence(seed=42)
        import collections.abc

        assert isinstance(seq, collections.abc.Sequence)


class TestLenAndGetItem:
    def test_empty_len(self):
        seq = RandomSequence(seed=42)
        assert len(seq) == 0

    def test_getitem_extends_cache(self):
        seq = RandomSequence(seed=42)
        val = seq[0]
        assert isinstance(val, int)
        assert len(seq) == 1

    def test_getitem_returns_in_range(self):
        seq = RandomSequence(seed=42, max=10)
        for i in range(100):
            assert 0 <= seq[i] <= 10

    def test_getitem_multiple_indices(self):
        seq = RandomSequence(seed=42)
        first = seq[0]
        second = seq[1]
        assert len(seq) == 2
        assert isinstance(first, int)
        assert isinstance(second, int)

    def test_getitem_non_sequential_access(self):
        seq = RandomSequence(seed=42)
        _ = seq[10]
        assert len(seq) >= 11
        assert all(seq[i] is not None for i in range(11))

    def test_getitem_all_values_deterministic(self):
        seq1 = RandomSequence(seed=12345)
        seq2 = RandomSequence(seed=12345)
        for i in range(50):
            assert seq1[i] == seq2[i]

    def test_getitem_len_matches_accessed(self):
        seq = RandomSequence(seed=42)
        _ = seq[5]
        assert len(seq) >= 6
        _ = seq[2]
        assert len(seq) >= 6


class TestDeterminism:
    def test_same_seed_same_sequence(self):
        a = RandomSequence(seed=999)
        b = RandomSequence(seed=999)
        for i in range(100):
            assert a[i] == b[i]

    def test_different_seed_different_sequence(self):
        a = RandomSequence(seed=1)
        b = RandomSequence(seed=2)
        same = all(a[i] == b[i] for i in range(10))
        assert not same

    def test_global_seed_independence(self):
        set_seed(0)
        a = RandomSequence(seed=777)
        vals_a = [a[i] for i in range(10)]
        set_seed(0)
        b = RandomSequence(seed=777)
        vals_b = [b[i] for i in range(10)]
        assert vals_a == vals_b


class TestGet:
    def test_get_returns_same_as_index(self):
        seq = RandomSequence(seed=42)
        assert seq.get(0) == seq[0]
        assert seq.get(5) == seq[5]
        assert seq.get(10) == seq[10]


class TestGetFloat:
    def test_get_float_range(self):
        seq = RandomSequence(seed=42, max=1000)
        for i in range(50):
            f = seq.get_float(i)
            assert 0 <= f <= 1

    def test_get_float_zero_max(self):
        seq = RandomSequence(seed=42, max=0)
        with pytest.raises(ZeroDivisionError):
            seq.get_float(0)

    def test_get_float_one_max(self):
        seq = RandomSequence(seed=42, max=1)
        for i in range(10):
            f = seq.get_float(i)
            assert f in (0.0, 1.0)

    def test_get_float_with_max_equals_self(self):
        seq = RandomSequence(seed=42, max=10)
        for i in range(20):
            assert seq.get_float(i) == pytest.approx(seq[i] / 10)


class TestGetArray:
    def test_get_array_from_zero(self):
        seq = RandomSequence(seed=42)
        arr = seq.get_array(0, 5)
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (5,)
        assert arr.dtype == np.intp
        assert list(arr) == [seq[i] for i in range(5)]

    def test_get_array_with_offset(self):
        seq = RandomSequence(seed=42)
        _ = seq[10]
        arr = seq.get_array(5, 8)
        assert arr.shape == (8,)
        assert list(arr) == [seq[i] for i in range(5, 13)]

    def test_get_array_extends_cache(self):
        seq = RandomSequence(seed=42)
        _ = seq[3]
        arr = seq.get_array(0, 20)
        assert len(arr) == 20
        assert len(seq) >= 20

    def test_get_array_empty_length(self):
        seq = RandomSequence(seed=42)
        arr = seq.get_array(0, 0)
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (0,)

    def test_get_array_deterministic(self):
        seq = RandomSequence(seed=42)
        assert list(seq.get_array(0, 10)) == list(seq.get_array(0, 10))

    def test_get_array_matches_slice(self):
        seq = RandomSequence(seed=42)
        arr = seq.get_array(3, 7)
        assert list(arr) == seq[3:10]

    def test_get_array_large(self):
        seq = RandomSequence(seed=42)
        arr = seq.get_array(0, 1000)
        assert arr.shape == (1000,)
        assert list(arr) == [seq[i] for i in range(1000)]


class TestGetArray01:
    def test_get_array_01_shape_and_dtype(self):
        seq = RandomSequence(seed=42, max=1000)
        arr = seq.get_array_01(0, 5)
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (5,)
        assert arr.dtype == np.float64

    def test_get_array_01_values_in_range(self):
        seq = RandomSequence(seed=42, max=1000)
        arr = seq.get_array_01(0, 100)
        assert (arr >= 0).all()
        assert (arr <= 1).all()

    def test_get_array_01_matches_get_float(self):
        seq = RandomSequence(seed=42, max=1000)
        arr = seq.get_array_01(0, 10)
        expected = np.array([seq.get_float(i) for i in range(10)], dtype=np.float64)
        assert arr == pytest.approx(expected)

    def test_get_array_01_matches_get_array_divided(self):
        seq = RandomSequence(seed=42, max=1000)
        arr = seq.get_array_01(3, 7)
        expected = seq.get_array(3, 7).astype(np.float64) / seq.max
        assert arr == pytest.approx(expected)

    def test_get_array_01_zero_max(self):
        import math

        seq = RandomSequence(seed=42, max=0)
        arr = seq.get_array_01(0, 1)
        assert math.isnan(arr[0])

    def test_get_array_01_extends_cache(self):
        seq = RandomSequence(seed=42, max=100)
        arr = seq.get_array_01(0, 20)
        assert len(arr) == 20
        assert len(seq) >= 20


class TestFork:
    def test_fork_deterministic(self):
        parent = RandomSequence(seed=42)
        child1 = parent.fork(5)
        child2 = parent.fork(5)
        for i in range(20):
            assert child1[i] == child2[i]

    def test_fork_different_index_different_sequence(self):
        parent = RandomSequence(seed=42)
        child_a = parent.fork(0)
        child_b = parent.fork(1)
        same = all(child_a[i] == child_b[i] for i in range(10))
        assert not same

    def test_fork_shares_max(self):
        parent = RandomSequence(seed=42, max=50)
        child = parent.fork(3)
        assert child.max == 50

    def test_fork_inherits_rng_factory(self):
        class CustomRandom(Random):
            pass

        parent = RandomSequence(seed=42, rng_factory=CustomRandom)
        child = parent.fork(0)
        assert isinstance(child._rng, CustomRandom)

    def test_fork_values_bounded(self):
        parent = RandomSequence(seed=42, max=7)
        child = parent.fork(2)
        for i in range(50):
            assert 0 <= child[i] <= 7


class TestMaxProperty:
    def test_max_positive(self):
        seq = RandomSequence(seed=42, max=255)
        assert seq.max == 255

    def test_max_zero(self):
        seq = RandomSequence(seed=42, max=0)
        for i in range(10):
            assert seq[i] == 0

    def test_max_one(self):
        seq = RandomSequence(seed=42, max=1)
        for i in range(10):
            assert seq[i] in (0, 1)


class TestRngFactory:
    def test_custom_factory(self):
        class CustomRandom(Random):
            pass

        seq = RandomSequence(seed=42, rng_factory=CustomRandom)
        assert isinstance(seq._rng, CustomRandom)

    def test_factory_with_none_seed(self):
        called_with = []

        def factory(seed):
            called_with.append(seed)
            return Random(seed)

        seq = RandomSequence(rng_factory=factory)
        _ = seq[0]
        assert len(called_with) == 1
        # seed was None; the factory should have received it
        assert called_with[0] is None

    def test_factory_passed_seed(self):
        called_with = []

        def factory(seed):
            called_with.append(seed)
            return Random(seed)

        _ = RandomSequence(seed=12345, rng_factory=factory)
        assert called_with == [12345]


class TestGetItemSlice:
    def test_basic_slice(self):
        seq = RandomSequence(seed=42)
        result = seq[0:5]
        assert isinstance(result, list)
        assert len(result) == 5
        assert all(isinstance(v, int) for v in result)
        assert len(seq) >= 5

    def test_slice_with_start(self):
        seq = RandomSequence(seed=42)
        _ = seq[5]
        result = seq[3:8]
        assert len(result) == 5
        assert result == [seq[i] for i in range(3, 8)]

    def test_slice_with_step(self):
        seq = RandomSequence(seed=42)
        result = seq[0:10:3]
        assert result == [seq[i] for i in range(0, 10, 3)]

    def test_slice_extends_cache(self):
        seq = RandomSequence(seed=42)
        _ = seq[0:20]
        assert len(seq) >= 20

    def test_slice_stop_extends_beyond_cache(self):
        seq = RandomSequence(seed=42)
        _ = seq[5]
        result = seq[2:15]
        assert len(result) == 13
        assert len(seq) >= 15

    def test_slice_no_stop_raises(self):
        seq = RandomSequence(seed=42)
        with pytest.raises(TypeError, match="requires an explicit stop"):
            seq[5:]

    def test_slice_negative_start_raises(self):
        seq = RandomSequence(seed=42)
        with pytest.raises(IndexError):
            seq[-5:10]

    def test_slice_negative_stop_raises(self):
        seq = RandomSequence(seed=42)
        with pytest.raises(IndexError):
            seq[0:-1]

    def test_slice_deterministic(self):
        seq = RandomSequence(seed=42)
        assert seq[0:10] == seq[0:10]

    def test_slice_result_values_match_individual_access(self):
        seq = RandomSequence(seed=42)
        sliced = seq[0:15]
        individual = [seq[i] for i in range(15)]
        assert sliced == individual

    def test_empty_slice(self):
        seq = RandomSequence(seed=42)
        _ = seq[5]
        result = seq[3:3]
        assert result == []
        assert len(seq) >= 6

    def test_slice_with_default_start(self):
        seq = RandomSequence(seed=42)
        result = seq[:5]
        assert result == [seq[i] for i in range(5)]

    def test_slice_with_step_beyond_cache(self):
        seq = RandomSequence(seed=42)
        _ = seq[3]
        result = seq[1:10:3]
        assert result == [seq[i] for i in range(1, 10, 3)]


class TestEdgeCases:
    def test_large_indices(self):
        seq = RandomSequence(seed=42)
        val = seq[10000]
        assert isinstance(val, int)
        assert len(seq) >= 10001

    def test_negative_index_raises(self):
        seq = RandomSequence(seed=42)
        with pytest.raises(IndexError):
            seq[-1]

    def test_repeated_access_same_index(self):
        seq = RandomSequence(seed=42)
        assert seq[5] == seq[5]

    def test_sequence_default_max_values_in_range(self):
        seq = RandomSequence(seed=42)
        for i in range(100):
            assert 0 <= seq[i] <= 0xFFFFFFFF


class TestThreadSafety:
    def test_concurrent_access(self):
        from concurrent.futures import ThreadPoolExecutor

        seq = RandomSequence(seed=42)
        results: list[int]

        def access(index: int) -> int:
            return seq[index]

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(access, range(200)))

        assert len(results) == 200
        assert all(isinstance(r, int) for r in results)
        assert len(seq) >= 200

    def test_concurrent_len_and_getitem(self):
        from concurrent.futures import ThreadPoolExecutor, as_completed

        seq = RandomSequence(seed=42)
        futures = []

        with ThreadPoolExecutor(max_workers=4) as pool:
            for i in range(100):
                futures.append(pool.submit(lambda i=i: (seq[i], len(seq))))

            for future in as_completed(futures):
                val, length = future.result()
                assert isinstance(val, int)
                assert length >= 0


class TestGrowthStrategy:
    def test_grows_to_power_of_two(self):
        seq = RandomSequence(seed=42)
        _ = seq[0]
        assert len(seq._cache) == 1
        _ = seq[1]
        assert len(seq._cache) == 2
        _ = seq[2]
        assert len(seq._cache) == 4
        _ = seq[3]
        assert len(seq._cache) == 4

    def test_grows_to_next_power_of_two_on_non_sequential_access(self):
        seq = RandomSequence(seed=42)
        _ = seq[5]
        assert len(seq._cache) == 8

    def test_growth_caps_at_4096(self):
        seq = RandomSequence(seed=42)
        _ = seq[4095]
        assert len(seq._cache) == 4096

    def test_growth_switches_to_block_mode_at_4097(self):
        seq = RandomSequence(seed=42)
        _ = seq[4096]
        assert len(seq._cache) == 8192

    def test_block_mode_growth(self):
        seq = RandomSequence(seed=42)
        _ = seq[10000]
        assert len(seq._cache) == 12288  # next multiple of 4096 above 10001

    def test_exact_block_boundary(self):
        seq = RandomSequence(seed=42)
        _ = seq[4096]
        assert len(seq._cache) == 8192
        _ = seq[8192]
        assert len(seq._cache) == 12288

    def test_array_values_correct_after_growth(self):
        seq = RandomSequence(seed=42)
        expected = [seq[i] for i in range(100)]
        assert len(seq._cache) == 128  # next power of two
        assert list(seq._cache[:100]) == expected
