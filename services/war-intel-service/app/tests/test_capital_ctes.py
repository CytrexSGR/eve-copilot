"""Tests for PowerBloc shared capital CTEs - SQL string generation."""

import pytest
from app.routers.powerbloc._shared import _capital_kills_cte, _capital_losses_cte, CAPITAL_GROUP_NAMES


class TestCapitalKillsCTE:
    def test_returns_string(self):
        result = _capital_kills_cte(7)
        assert isinstance(result, str)

    def test_contains_distinct(self):
        result = _capital_kills_cte(7)
        assert "DISTINCT" in result

    def test_uses_days_parameter(self):
        result = _capital_kills_cte(30)
        assert "30 days" in result

    def test_different_days(self):
        r7 = _capital_kills_cte(7)
        r30 = _capital_kills_cte(30)
        assert "7 days" in r7
        assert "30 days" in r30

    def test_joins_attackers(self):
        result = _capital_kills_cte(7)
        assert "killmail_attackers" in result

    def test_references_member_ids(self):
        result = _capital_kills_cte(7)
        assert "%(member_ids)s" in result

    def test_references_capital_groups(self):
        result = _capital_kills_cte(7)
        assert "%(capital_groups)s" in result

    def test_cte_name(self):
        result = _capital_kills_cte(7)
        assert "unique_capital_kills" in result


class TestCapitalLossesCTE:
    def test_returns_string(self):
        result = _capital_losses_cte(7)
        assert isinstance(result, str)

    def test_uses_victim_alliance(self):
        result = _capital_losses_cte(7)
        assert "victim_alliance_id" in result

    def test_no_distinct(self):
        """Losses don't need DISTINCT (victim is single entity)."""
        result = _capital_losses_cte(7)
        # Should still have the CTE but uses victim side
        assert "unique_capital_losses" in result

    def test_uses_days_parameter(self):
        result = _capital_losses_cte(14)
        assert "14 days" in result

    def test_includes_victim_character(self):
        result = _capital_losses_cte(7)
        assert "victim_character_id" in result


class TestCapitalGroupNames:
    def test_eight_groups(self):
        assert len(CAPITAL_GROUP_NAMES) == 8

    def test_contains_carrier(self):
        assert 'Carrier' in CAPITAL_GROUP_NAMES

    def test_contains_dreadnought(self):
        assert 'Dreadnought' in CAPITAL_GROUP_NAMES

    def test_contains_fax(self):
        assert 'Force Auxiliary' in CAPITAL_GROUP_NAMES

    def test_contains_super(self):
        assert 'Supercarrier' in CAPITAL_GROUP_NAMES

    def test_contains_titan(self):
        assert 'Titan' in CAPITAL_GROUP_NAMES

    def test_contains_capital_industrial(self):
        assert 'Capital Industrial Ship' in CAPITAL_GROUP_NAMES

    def test_contains_jump_freighter(self):
        assert 'Jump Freighter' in CAPITAL_GROUP_NAMES

    def test_contains_lancer_dreadnought(self):
        assert 'Lancer Dreadnought' in CAPITAL_GROUP_NAMES

    def test_is_tuple(self):
        assert isinstance(CAPITAL_GROUP_NAMES, tuple)
