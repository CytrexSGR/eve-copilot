"""Tests for EntityContext — SQL filter generation per entity type."""

import pytest
from app.routers.intelligence.entity_context import EntityContext, EntityType


@pytest.fixture
def alliance_ctx():
    return EntityContext(entity_type=EntityType.ALLIANCE, entity_id=99003581)


@pytest.fixture
def corp_ctx():
    return EntityContext(entity_type=EntityType.CORPORATION, entity_id=98378388, alliance_id_for_sov=99003581)


@pytest.fixture
def powerbloc_ctx():
    return EntityContext(entity_type=EntityType.POWERBLOC, member_ids=[99003581, 99001234, 99005678])


class TestFilterValue:
    def test_alliance_returns_entity_id(self, alliance_ctx):
        assert alliance_ctx.filter_value == 99003581

    def test_corp_returns_entity_id(self, corp_ctx):
        assert corp_ctx.filter_value == 98378388

    def test_powerbloc_returns_member_ids(self, powerbloc_ctx):
        assert powerbloc_ctx.filter_value == [99003581, 99001234, 99005678]


class TestKillAttackerFilter:
    def test_alliance_uses_alliance_id(self, alliance_ctx):
        assert "c.alliance_id = %s" == alliance_ctx.kill_attacker_filter

    def test_corp_uses_corporation_id(self, corp_ctx):
        assert "ka.corporation_id = %s" == corp_ctx.kill_attacker_filter

    def test_powerbloc_uses_any(self, powerbloc_ctx):
        assert "c.alliance_id = ANY(%s)" == powerbloc_ctx.kill_attacker_filter


class TestDeathVictimFilter:
    def test_alliance_uses_alliance_id(self, alliance_ctx):
        assert "c.alliance_id = %s" == alliance_ctx.death_victim_filter

    def test_corp_uses_victim_corporation_id(self, corp_ctx):
        assert "km.victim_corporation_id = %s" == corp_ctx.death_victim_filter

    def test_powerbloc_uses_any(self, powerbloc_ctx):
        assert "c.alliance_id = ANY(%s)" == powerbloc_ctx.death_victim_filter


class TestCorpJoinNeeded:
    def test_alliance_needs_corp_join_for_kills(self, alliance_ctx):
        assert alliance_ctx.kill_attacker_needs_corp_join is True

    def test_corp_does_not_need_corp_join_for_kills(self, corp_ctx):
        assert corp_ctx.kill_attacker_needs_corp_join is False

    def test_powerbloc_needs_corp_join_for_kills(self, powerbloc_ctx):
        assert powerbloc_ctx.kill_attacker_needs_corp_join is True

    def test_alliance_needs_corp_join_for_deaths(self, alliance_ctx):
        assert alliance_ctx.death_victim_needs_corp_join is True

    def test_corp_does_not_need_corp_join_for_deaths(self, corp_ctx):
        assert corp_ctx.death_victim_needs_corp_join is False


class TestSovFilter:
    def test_alliance_sov_filter(self, alliance_ctx):
        assert "sov.alliance_id = %s" == alliance_ctx.sov_filter

    def test_powerbloc_sov_filter(self, powerbloc_ctx):
        assert "sov.alliance_id = ANY(%s)" == powerbloc_ctx.sov_filter


class TestSovValue:
    def test_alliance_sov_value_equals_entity_id(self, alliance_ctx):
        assert alliance_ctx.sov_value == 99003581

    def test_corp_sov_value_uses_alliance_id_for_sov(self, corp_ctx):
        assert corp_ctx.sov_value == 99003581

    def test_powerbloc_sov_value_equals_member_ids(self, powerbloc_ctx):
        assert powerbloc_ctx.sov_value == [99003581, 99001234, 99005678]


class TestCapitalFilters:
    def test_alliance_capital_kill_filter(self, alliance_ctx):
        assert "ka.alliance_id = %(entity_id)s" == alliance_ctx.capital_kill_filter

    def test_corp_capital_kill_filter(self, corp_ctx):
        assert "ka.corporation_id = %(entity_id)s" == corp_ctx.capital_kill_filter

    def test_powerbloc_capital_kill_filter(self, powerbloc_ctx):
        assert "ka.alliance_id = ANY(%(entity_id)s)" == powerbloc_ctx.capital_kill_filter

    def test_alliance_capital_loss_filter(self, alliance_ctx):
        assert "km.victim_alliance_id = %(entity_id)s" == alliance_ctx.capital_loss_filter

    def test_corp_capital_loss_filter(self, corp_ctx):
        assert "km.victim_corporation_id = %(entity_id)s" == corp_ctx.capital_loss_filter

    def test_powerbloc_capital_loss_filter(self, powerbloc_ctx):
        assert "km.victim_alliance_id = ANY(%(entity_id)s)" == powerbloc_ctx.capital_loss_filter


class TestCapitalSqlParams:
    def test_alliance_params(self, alliance_ctx):
        assert alliance_ctx.capital_sql_params == {"entity_id": 99003581}

    def test_corp_params(self, corp_ctx):
        assert corp_ctx.capital_sql_params == {"entity_id": 98378388}

    def test_powerbloc_params(self, powerbloc_ctx):
        assert powerbloc_ctx.capital_sql_params == {"entity_id": [99003581, 99001234, 99005678]}


class TestParamHelpers:
    def test_region_params(self, alliance_ctx):
        assert alliance_ctx.region_params(30) == (99003581, 30, 99003581, 30)

    def test_home_params_alliance(self, alliance_ctx):
        assert alliance_ctx.home_params(30) == (99003581, 30, 99003581, 30, 99003581)

    def test_home_params_corp(self, corp_ctx):
        # Corp uses alliance_id_for_sov for the sov value
        assert corp_ctx.home_params(30) == (98378388, 30, 98378388, 30, 99003581)

    def test_home_params_powerbloc(self, powerbloc_ctx):
        member_ids = [99003581, 99001234, 99005678]
        assert powerbloc_ctx.home_params(30) == (member_ids, 30, member_ids, 30, member_ids)
