"""Tests for dynamic DPS enrichment in fleet_comp."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestEnrichDoctrineStats:

    @pytest.mark.asyncio
    async def test_enrichment_with_dogma_stats(self):
        from app.routers.fleet_comp import enrich_doctrine_stats

        with patch("app.routers.fleet_comp.resolve_doctrine_id", return_value=12):
            with patch("app.routers.fleet_comp.get_doctrine_stats", new_callable=AsyncMock) as mock_stats:
                mock_stats.return_value = {
                    "dps": 547.2, "ehp": 42000, "tank_type": "armor",
                    "cap_stable": True, "weapon_dps": 500, "drone_dps": 47.2,
                }
                result = await enrich_doctrine_stats("Muninn Fleet", db=MagicMock())
                assert result["avg_dps"] == 547.2
                assert result["ehp"] == 42000
                assert result["source"] == "dogma"
                assert result["tank"] == "armor"
                assert result["cap_stable"] is True
                assert result["weapon_dps"] == 500
                assert result["drone_dps"] == 47.2
                # Hardcoded counter info preserved
                assert result["range"] == "long"
                assert result["weapon"] == "artillery"
                assert result["counters"] == ["Cerberus Fleet", "Eagle Fleet"]

    @pytest.mark.asyncio
    async def test_enrichment_fallback_on_failure(self):
        from app.routers.fleet_comp import enrich_doctrine_stats

        with patch("app.routers.fleet_comp.resolve_doctrine_id", return_value=None):
            result = await enrich_doctrine_stats("Muninn Fleet", db=MagicMock())
            assert result["avg_dps"] == 520  # hardcoded default
            assert result["source"] == "hardcoded"
            assert result["ehp"] == 0

    @pytest.mark.asyncio
    async def test_enrichment_unknown_doctrine(self):
        from app.routers.fleet_comp import enrich_doctrine_stats
        result = await enrich_doctrine_stats("Unknown Doctrine 9999", db=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_enrichment_no_db_uses_hardcoded(self):
        from app.routers.fleet_comp import enrich_doctrine_stats
        result = await enrich_doctrine_stats("Ferox Fleet", db=None)
        assert result["avg_dps"] == 400
        assert result["source"] == "hardcoded"
        assert result["ehp"] == 0
        assert result["tank"] == "shield"
        assert result["range"] == "medium"

    @pytest.mark.asyncio
    async def test_enrichment_dogma_returns_none_falls_back(self):
        """When Dogma Engine returns None stats, fall back to hardcoded."""
        from app.routers.fleet_comp import enrich_doctrine_stats

        with patch("app.routers.fleet_comp.resolve_doctrine_id", return_value=12):
            with patch("app.routers.fleet_comp.get_doctrine_stats", new_callable=AsyncMock) as mock_stats:
                mock_stats.return_value = None
                result = await enrich_doctrine_stats("Ferox Fleet", db=MagicMock())
                assert result["avg_dps"] == 400
                assert result["source"] == "hardcoded"

    @pytest.mark.asyncio
    async def test_enrichment_unknown_doctrine_with_db(self):
        """Unknown doctrine with db still returns None when not in KNOWN_DOCTRINES."""
        from app.routers.fleet_comp import enrich_doctrine_stats

        with patch("app.routers.fleet_comp.resolve_doctrine_id", return_value=None):
            result = await enrich_doctrine_stats("Unknown Doctrine 9999", db=MagicMock())
            assert result is None

    @pytest.mark.asyncio
    async def test_enrichment_ship_name_extraction(self):
        """Verifies 'Muninn Fleet' strips to 'Muninn' for resolve call."""
        from app.routers.fleet_comp import enrich_doctrine_stats

        with patch("app.routers.fleet_comp.resolve_doctrine_id", return_value=None) as mock_resolve:
            with patch("app.routers.fleet_comp.get_doctrine_stats", new_callable=AsyncMock):
                await enrich_doctrine_stats("Muninn Fleet", db=MagicMock())
                mock_resolve.assert_called_once()
                assert mock_resolve.call_args[0][1] == "Muninn"

    @pytest.mark.asyncio
    async def test_enrichment_dogma_unknown_ship_preserves_defaults(self):
        """Dogma enrichment for a doctrine not in KNOWN_DOCTRINES uses default range/weapon."""
        from app.routers.fleet_comp import enrich_doctrine_stats

        with patch("app.routers.fleet_comp.resolve_doctrine_id", return_value=99):
            with patch("app.routers.fleet_comp.get_doctrine_stats", new_callable=AsyncMock) as mock_stats:
                mock_stats.return_value = {
                    "dps": 300, "ehp": 20000, "tank_type": "shield",
                    "cap_stable": False, "weapon_dps": 280, "drone_dps": 20,
                }
                result = await enrich_doctrine_stats("Custom Doctrine Fleet", db=MagicMock())
                assert result["avg_dps"] == 300
                assert result["source"] == "dogma"
                assert result["range"] == "medium"  # default
                assert result["weapon"] == "unknown"  # default
                assert result["counters"] == []  # default


class TestBuildCounterResponse:

    def test_response_with_enriched_stats(self):
        from app.routers.fleet_comp import _build_counter_response
        enriched = {"avg_dps": 547.2, "ehp": 42000, "tank": "armor", "source": "dogma"}
        response = _build_counter_response("Muninn Fleet", 30, enriched)
        assert response["enemy_doctrine"] == "Muninn Fleet"
        assert response["enemy_dps_per_ship"] == 547.2
        assert response["enemy_total_dps"] == pytest.approx(547.2 * 30, rel=0.01)
        assert response["enemy_ehp"] == 42000
        assert response["enemy_tank"] == "armor"
        assert response["dps_source"] == "dogma"

    def test_response_with_hardcoded_stats(self):
        from app.routers.fleet_comp import _build_counter_response
        enriched = {"avg_dps": 520, "ehp": 0, "tank": "armor", "source": "hardcoded"}
        response = _build_counter_response("Muninn Fleet", 30, enriched)
        assert response["enemy_dps_per_ship"] == 520
        assert response["enemy_total_dps"] == 15600.0
        assert response["dps_source"] == "hardcoded"

    def test_response_defaults_for_missing_keys(self):
        from app.routers.fleet_comp import _build_counter_response
        enriched = {}
        response = _build_counter_response("Test Fleet", 10, enriched)
        assert response["enemy_dps_per_ship"] == 400  # default
        assert response["enemy_total_dps"] == 4000.0
        assert response["enemy_ehp"] == 0
        assert response["enemy_tank"] == "unknown"
        assert response["dps_source"] == "hardcoded"

    def test_response_single_ship(self):
        from app.routers.fleet_comp import _build_counter_response
        enriched = {"avg_dps": 600, "ehp": 50000, "tank": "shield", "source": "dogma"}
        response = _build_counter_response("Nightmare Fleet", 1, enriched)
        assert response["enemy_total_dps"] == 600.0
        assert response["enemy_ehp"] == 50000
