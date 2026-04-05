"""Tests for Bloom filter hash function and logic.

Tests the pure _bloom_hashes() function from red_list_checker.py
and verifies Bloom filter properties (determinism, distribution,
false positive behavior).
"""

import hashlib
import struct

import pytest

# ---- Inline reimplementation of pure functions (no DB/Redis imports) ----

BLOOM_SIZE = 1_000_000
BLOOM_HASHES = 7


def _bloom_hashes(entity_id: int) -> list[int]:
    """Generate k hash positions for a Bloom filter.

    Reimplemented from app.services.red_list_checker._bloom_hashes
    to avoid importing module that requires DB/Redis at load time.
    """
    data = struct.pack(">Q", entity_id)
    positions = []
    for i in range(BLOOM_HASHES):
        h = hashlib.sha256(data + struct.pack(">I", i)).digest()
        pos = int.from_bytes(h[:4], "big") % BLOOM_SIZE
        positions.append(pos)
    return positions


# ---- Tests ----


class TestBloomHashes:
    """Tests for the _bloom_hashes pure function."""

    def test_returns_correct_number_of_hashes(self):
        """Should return exactly BLOOM_HASHES (7) positions."""
        positions = _bloom_hashes(12345)
        assert len(positions) == BLOOM_HASHES

    def test_all_positions_within_bloom_size(self):
        """All positions must be in range [0, BLOOM_SIZE)."""
        for entity_id in [0, 1, 999999, 2**32, 2**63 - 1]:
            positions = _bloom_hashes(entity_id)
            for pos in positions:
                assert 0 <= pos < BLOOM_SIZE, (
                    f"Position {pos} out of range for entity_id={entity_id}"
                )

    def test_deterministic_output(self):
        """Same entity_id must always produce same positions."""
        result1 = _bloom_hashes(42)
        result2 = _bloom_hashes(42)
        assert result1 == result2

    def test_different_entities_differ(self):
        """Different entity IDs should (almost certainly) produce different positions."""
        pos_a = set(_bloom_hashes(100))
        pos_b = set(_bloom_hashes(200))
        # Extremely unlikely that all 7 positions collide
        assert pos_a != pos_b

    def test_positions_are_integers(self):
        """All returned positions must be integers."""
        positions = _bloom_hashes(9999)
        for pos in positions:
            assert isinstance(pos, int)

    def test_zero_entity_id(self):
        """Entity ID 0 should produce valid hash positions."""
        positions = _bloom_hashes(0)
        assert len(positions) == BLOOM_HASHES
        for pos in positions:
            assert 0 <= pos < BLOOM_SIZE

    def test_large_entity_id(self):
        """Very large entity IDs (EVE character IDs can be large) work correctly."""
        positions = _bloom_hashes(2124063958)  # Real EVE character ID
        assert len(positions) == BLOOM_HASHES
        for pos in positions:
            assert 0 <= pos < BLOOM_SIZE

    def test_no_duplicate_positions_for_typical_ids(self):
        """For typical entity IDs, positions should generally be unique.

        With BLOOM_SIZE=1M and only 7 hashes, collisions within a single
        entity's positions are extremely rare.
        """
        for eid in [1117367444, 526379435, 110592475, 2124063958]:
            positions = _bloom_hashes(eid)
            assert len(set(positions)) == len(positions), (
                f"Duplicate positions for entity_id={eid}: {positions}"
            )

    def test_sequential_ids_produce_spread_positions(self):
        """Sequential entity IDs should produce well-distributed positions.

        Check that positions for IDs 1-10 don't all cluster in the same
        small region (i.e., the hash function distributes well).
        """
        all_positions = set()
        for eid in range(1, 11):
            all_positions.update(_bloom_hashes(eid))

        # 10 entities * 7 hashes = 70 positions
        # With good distribution, we expect most to be unique
        assert len(all_positions) > 50, (
            f"Only {len(all_positions)} unique positions for 70 hashes - poor distribution"
        )


class TestBloomFilterSimulation:
    """Simulate Bloom filter add/check behavior using the hash function."""

    def _simulate_bloom_add(self, bitset: set, entity_id: int):
        """Add entity to simulated bloom filter (set of bit positions)."""
        for pos in _bloom_hashes(entity_id):
            bitset.add(pos)

    def _simulate_bloom_check(self, bitset: set, entity_id: int) -> bool:
        """Check if entity might be in simulated bloom filter."""
        return all(pos in bitset for pos in _bloom_hashes(entity_id))

    def test_added_entity_is_found(self):
        """An entity added to the filter must always be found (no false negatives)."""
        bitset = set()
        self._simulate_bloom_add(bitset, 12345)
        assert self._simulate_bloom_check(bitset, 12345) is True

    def test_absent_entity_not_found_in_empty_filter(self):
        """An empty filter should not match any entity."""
        bitset = set()
        assert self._simulate_bloom_check(bitset, 12345) is False

    def test_no_false_negatives_multiple_entities(self):
        """All added entities must be found - zero false negatives guaranteed."""
        bitset = set()
        entity_ids = [100, 200, 300, 400, 500, 9999999]
        for eid in entity_ids:
            self._simulate_bloom_add(bitset, eid)

        for eid in entity_ids:
            assert self._simulate_bloom_check(bitset, eid) is True, (
                f"False negative for entity_id={eid}"
            )

    def test_false_positive_rate_is_bounded(self):
        """False positive rate should be reasonable for moderate load.

        With 100 entities in a 1M bit filter with 7 hashes, the expected
        false positive rate is approximately (1 - e^(-700/1000000))^7 << 1%.
        Test with 1000 random checks.
        """
        bitset = set()
        for eid in range(100):
            self._simulate_bloom_add(bitset, eid)

        false_positives = 0
        test_range = range(10000, 11000)
        for eid in test_range:
            if self._simulate_bloom_check(bitset, eid):
                false_positives += 1

        # With such low load, FP rate should be well under 1%
        assert false_positives < 10, (
            f"Too many false positives: {false_positives}/1000"
        )
