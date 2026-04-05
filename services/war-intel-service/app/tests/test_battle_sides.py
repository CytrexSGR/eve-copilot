"""Tests for BFS 2-coloring battle side determination."""

import pytest
from app.routers.war.battles.sides import determine_sides


def _rel(attacker: int, victim: int, kills: int = 1) -> dict:
    """Helper to build a kill_relations entry."""
    return {"attacker_alliance": attacker, "victim_alliance": victim, "kills": kills}


# ---------------------------------------------------------------------------
# Basic 2-sided battles
# ---------------------------------------------------------------------------

class TestSimpleTwoSided:
    def test_a_kills_b(self):
        """A kills B → opposite sides."""
        rels = [_rel(1, 2)]
        a, b = determine_sides(rels, {}, {})
        assert (1 in a and 2 in b) or (2 in a and 1 in b)
        assert a & b == set()

    def test_a_kills_b_seed_selection(self):
        """More involved alliance becomes side_a seed."""
        rels = [_rel(1, 2, kills=10)]
        a, b = determine_sides(rels, {}, {})
        # Alliance 1 has 10 kills, 2 has 0 kills + 10 losses → both =10
        # max picks 1 first (arbitrary but deterministic)
        assert 1 in a
        assert 2 in b

    def test_symmetric_kills(self):
        """Both kill each other → still opposite sides."""
        rels = [_rel(1, 2, kills=5), _rel(2, 1, kills=3)]
        a, b = determine_sides(rels, {}, {})
        assert (1 in a and 2 in b) or (2 in a and 1 in b)


class TestTransitiveAllies:
    def test_shared_enemy_same_side(self):
        """A kills B, C kills B → A and C on same side."""
        rels = [_rel(1, 2, kills=5), _rel(3, 2, kills=3)]
        a, b = determine_sides(rels, {}, {})
        # 1 and 3 should be on the same side, 2 on the other
        if 1 in a:
            assert 3 in a
            assert 2 in b
        else:
            assert 3 in b
            assert 2 in a

    def test_shared_attacker_same_side(self):
        """A kills B, A kills C → B and C on same side (co-victims)."""
        rels = [_rel(1, 2, kills=5), _rel(1, 3, kills=3)]
        a, b = determine_sides(rels, {}, {})
        if 2 in a:
            assert 3 in a
            assert 1 in b
        else:
            assert 3 in b
            assert 1 in a


class TestMultipleAlliances:
    def test_three_vs_one(self):
        """A, B, C all kill D → A, B, C on same side."""
        rels = [_rel(1, 4), _rel(2, 4), _rel(3, 4)]
        a, b = determine_sides(rels, {}, {})
        if 4 in a:
            assert {1, 2, 3} <= b
        else:
            assert {1, 2, 3} <= a

    def test_two_vs_two(self):
        """A kills C, B kills D, A kills D → {A,B} vs {C,D}."""
        rels = [_rel(1, 3), _rel(2, 4), _rel(1, 4)]
        a, b = determine_sides(rels, {}, {})
        # 1 and 2 should share a side, 3 and 4 the other
        if 1 in a:
            assert 2 in a
            assert {3, 4} <= b
        else:
            assert 2 in b
            assert {3, 4} <= a

    def test_chain_of_enemies(self):
        """A kills B, B kills C → A and C on same side (enemy-of-enemy)."""
        rels = [_rel(1, 2, kills=5), _rel(2, 3, kills=3)]
        a, b = determine_sides(rels, {}, {})
        if 1 in a:
            assert 3 in a
            assert 2 in b
        else:
            assert 3 in b
            assert 2 in a


# ---------------------------------------------------------------------------
# Disconnected components
# ---------------------------------------------------------------------------

class TestDisconnectedComponents:
    def test_two_independent_fights(self):
        """A↔B and C↔D fight independently → both pairs split."""
        rels = [_rel(1, 2, kills=10), _rel(3, 4, kills=5)]
        a, b = determine_sides(rels, {}, {})
        # Each pair must be split across sides
        assert not ({1, 2} <= a or {1, 2} <= b)
        assert not ({3, 4} <= a or {3, 4} <= b)

    def test_isolated_alliance_joins_higher_involvement(self):
        """Disconnected alliance seeded into side_a of its component."""
        rels = [_rel(1, 2, kills=100), _rel(3, 4, kills=1)]
        a, b = determine_sides(rels, {}, {})
        # Alliance 1 (100 kills) is most involved overall → side_a
        assert 1 in a
        assert 2 in b


# ---------------------------------------------------------------------------
# Seed selection (most involved alliance)
# ---------------------------------------------------------------------------

class TestSeedSelection:
    def test_highest_involvement_becomes_seed(self):
        """Alliance with most kills+losses starts as side_a."""
        # Alliance 3 has 20 kills, others have fewer
        rels = [_rel(3, 1, kills=20), _rel(3, 2, kills=5), _rel(1, 3, kills=2)]
        a, b = determine_sides(rels, {}, {})
        # Alliance 3: 25 kills + 2 losses = 27 involvement
        # Alliance 1: 2 kills + 20 losses = 22 involvement
        assert 3 in a


# ---------------------------------------------------------------------------
# Coalition consolidation
# ---------------------------------------------------------------------------

class TestCoalitionConsolidation:
    def test_split_coalition_consolidated_by_pilots(self):
        """Coalition members from disconnected components → consolidated to same side."""
        # Component 1: {1,3} kill 2 → 2 (inv=15) → side_a, {1,3} → side_b
        # Component 2: 4 kills {5,6} → 4 (inv=4) → side_a, {5,6} → side_b
        # Coalition 100: {2, 5} → 2 in side_a, 5 in side_b → split
        # 2 has 50 pilots > 5 has 10 → consolidate 5 to side_a
        rels = [_rel(1, 2, kills=10), _rel(3, 2, kills=5),
                _rel(4, 5, kills=3), _rel(4, 6, kills=1)]
        pilots = {2: 50, 5: 10}
        coalitions = {2: 100, 5: 100}

        a, b = determine_sides(rels, pilots, coalitions)
        # 2 and 5 should end up on the same side after consolidation
        assert (2 in a and 5 in a) or (2 in b and 5 in b)

    def test_split_coalition_moves_to_larger_side(self):
        """Coalition minority moves to majority side (by pilot count)."""
        # Same topology as above, but 5 has more pilots → 2 moves to side_b
        rels = [_rel(1, 2, kills=10), _rel(3, 2, kills=5),
                _rel(4, 5, kills=3), _rel(4, 6, kills=1)]
        pilots = {2: 5, 5: 30}
        coalitions = {2: 100, 5: 100}

        a, b = determine_sides(rels, pilots, coalitions)
        # 2 and 5 on same side; 5 had more pilots so 2 moved to 5's side
        assert (2 in a and 5 in a) or (2 in b and 5 in b)

    def test_no_coalition_no_consolidation(self):
        """Without coalition data, sides stay as BFS assigned."""
        rels = [_rel(1, 2)]
        a, b = determine_sides(rels, {}, {})
        assert a & b == set()
        assert a | b == {1, 2}


class TestCoalitionInternalConflict:
    def test_internal_conflict_blocks_consolidation(self):
        """Coalition members fighting each other → no consolidation."""
        # 1 kills 2 → opposite sides
        # Both in coalition 100, but they fight each other
        rels = [_rel(1, 2, kills=5)]
        pilots = {1: 50, 2: 10}
        coalitions = {1: 100, 2: 100}

        a, b = determine_sides(rels, pilots, coalitions)
        # Should NOT consolidate because 1 and 2 are enemies
        assert (1 in a and 2 in b) or (1 in b and 2 in a)

    def test_indirect_conflict_allows_consolidation(self):
        """Coalition members on opposite sides but NOT directly fighting → consolidate."""
        # 1 kills 3, 2 kills 3 → {1,2} vs {3}
        # Then 4 kills 1 → 4 on side with 3, 1 stays on side_a
        # If 2 and 4 are in coalition (leader=200), and they don't fight each other
        # directly, consolidation should happen
        rels = [_rel(1, 3, kills=10), _rel(2, 3, kills=5), _rel(4, 1, kills=3)]
        pilots = {1: 20, 2: 15, 3: 10, 4: 30}
        # 2 is on side with 1 (co-attackers of 3), 4 is on side with 3 (both attack 1)
        coalitions = {2: 200, 4: 200}

        a, b = determine_sides(rels, pilots, coalitions)
        # 2 and 4 don't directly fight → consolidation should happen
        assert (2 in a and 4 in a) or (2 in b and 4 in b)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_single_alliance(self):
        """Only one alliance appears (kills itself?) → side_a only."""
        rels = [_rel(1, 1, kills=3)]
        a, b = determine_sides(rels, {}, {})
        assert 1 in a
        # Self-kill: enemy_adj has 1→{1}, BFS assigns 1 to side_a,
        # then neighbor=1 is already assigned → no change
        assert b == set() or 1 not in b

    def test_empty_pilot_counts_uses_default(self):
        """Missing pilot counts default to 1 in consolidation."""
        # Same disconnected topology — coalition members on different sides
        rels = [_rel(1, 2, kills=10), _rel(3, 2, kills=5),
                _rel(4, 5, kills=3), _rel(4, 6, kills=1)]
        coalitions = {2: 100, 5: 100}
        # No pilot counts → both default to 1, a_pilots >= b_pilots → consolidate
        a, b = determine_sides(rels, {}, coalitions)
        assert (2 in a and 5 in a) or (2 in b and 5 in b)

    def test_many_alliances(self):
        """Stress test with 20 alliances in a complex battle."""
        rels = []
        # Side A: alliances 1-10 all kill alliance 100
        for i in range(1, 11):
            rels.append(_rel(i, 100, kills=i))
        # Side B: alliance 100 kills back
        rels.append(_rel(100, 1, kills=50))
        # Alliance 200 kills alliance 1 (joins side B with 100)
        rels.append(_rel(200, 1, kills=5))

        a, b = determine_sides(rels, {}, {})
        # 100 and 200 should be on the same side (both attack 1)
        assert (100 in a and 200 in a) or (100 in b and 200 in b)
        # All of 1-10 should be on the other side
        attackers = {i for i in range(1, 11)}
        if 100 in a:
            assert attackers <= b
        else:
            assert attackers <= a

    def test_returns_tuple_of_sets(self):
        """Return type is a tuple of two sets."""
        rels = [_rel(1, 2)]
        result = determine_sides(rels, {}, {})
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], set)
        assert isinstance(result[1], set)

    def test_all_alliances_accounted_for(self):
        """Every alliance from kill_relations appears in exactly one side."""
        rels = [_rel(1, 2), _rel(3, 4), _rel(1, 4)]
        a, b = determine_sides(rels, {}, {})
        assert a | b == {1, 2, 3, 4}
        assert a & b == set()
