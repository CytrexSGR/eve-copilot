import pytest
from app.tests.conftest import MockCursor, MultiResultCursor


class TestThreatCompositionSQL:
    """Test that SQL queries are constructed correctly."""

    def test_alliance_threat_query_uses_victim_filter(self):
        """Threat composition should look at kills WHERE WE are the victim."""
        from app.routers.intelligence.threats import _build_threat_query
        sql, params = _build_threat_query("alliance", 99003581, 30)
        assert "victim" in sql.lower()
        assert 99003581 in params
        assert 30 in params

    def test_corp_threat_query_uses_corp_filter(self):
        from app.routers.intelligence.threats import _build_threat_query
        sql, params = _build_threat_query("corporation", 98378388, 30)
        assert "corporation_id" in sql.lower()
        assert 98378388 in params


class TestDamageProfileAggregation:
    def test_aggregate_damage_profiles(self):
        from app.routers.intelligence.threats import _aggregate_damage_profile
        weapons = [
            {"em_pct": 0.5, "thermal_pct": 0.5, "kinetic_pct": 0.0, "explosive_pct": 0.0, "count": 10},
            {"em_pct": 0.0, "thermal_pct": 0.0, "kinetic_pct": 0.5, "explosive_pct": 0.5, "count": 10},
        ]
        result = _aggregate_damage_profile(weapons)
        assert result["em"] == pytest.approx(0.25, abs=0.01)
        assert result["kinetic"] == pytest.approx(0.25, abs=0.01)

    def test_empty_weapons(self):
        from app.routers.intelligence.threats import _aggregate_damage_profile
        result = _aggregate_damage_profile([])
        assert result == {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 0}
