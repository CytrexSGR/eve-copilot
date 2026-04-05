"""Tests for DPS enrichment in fitting analyzer."""


class TestShipClassDpsEstimates:
    def test_hardcoded_values_exist(self):
        from app.services.dogma.fitting_analyzer import SHIP_CLASS_DPS_ESTIMATES
        assert SHIP_CLASS_DPS_ESTIMATES["cruiser"] == 400
        assert SHIP_CLASS_DPS_ESTIMATES["battleship"] == 900
        assert SHIP_CLASS_DPS_ESTIMATES["dreadnought"] == 10000
        assert SHIP_CLASS_DPS_ESTIMATES["frigate"] == 150


class TestGetShipDps:
    def test_with_override(self):
        from app.services.dogma.fitting_analyzer import get_ship_dps
        overrides = {12015: 547.2}  # Muninn
        result = get_ship_dps(12015, "heavy_assault_cruiser", overrides)
        assert result == 547.2

    def test_without_override_uses_class(self):
        from app.services.dogma.fitting_analyzer import get_ship_dps
        result = get_ship_dps(99999, "cruiser", {})
        assert result == 400

    def test_no_overrides_dict(self):
        from app.services.dogma.fitting_analyzer import get_ship_dps
        result = get_ship_dps(99999, "battleship", None)
        assert result == 900

    def test_unknown_class_returns_default(self):
        from app.services.dogma.fitting_analyzer import get_ship_dps
        result = get_ship_dps(99999, "unknown_class", {})
        assert result == 200

    def test_override_takes_precedence(self):
        from app.services.dogma.fitting_analyzer import get_ship_dps
        # Even if class says 400, override says 1000
        overrides = {12345: 1000.0}
        result = get_ship_dps(12345, "cruiser", overrides)
        assert result == 1000.0

    def test_empty_overrides_uses_class(self):
        from app.services.dogma.fitting_analyzer import get_ship_dps
        result = get_ship_dps(12015, "heavy_assault_cruiser", {})
        assert result == 550  # HAC default
