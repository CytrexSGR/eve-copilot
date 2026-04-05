"""Integration tests for the full Dogma pipeline via calculate_modified_attributes."""
import pytest
from unittest.mock import MagicMock, patch
from app.services.dogma.engine import DogmaEngine


class TestCalculateModifiedAttributesIntegration:
    """Test the full pipeline with mocked DB calls."""

    def test_empty_fit_returns_ship_base_attrs(self):
        """Ship with no modules should return base attributes."""
        # Patch all DB-touching methods to return empty/base data
        engine = DogmaEngine.__new__(DogmaEngine)
        engine.db = MagicMock()

        ship_type_id = 29990
        ship_attrs = {263: 5000.0, 265: 3000.0, 9: 2000.0, 48: 300.0, 11: 1000.0}

        with patch.object(engine, '_load_all_attributes', return_value={
            ship_type_id: dict(ship_attrs),
        }):
            with patch.object(engine, '_supplement_invtypes_attrs', side_effect=lambda tid, a: a):
                with patch.object(engine, '_load_group_ids', return_value={}):
                    with patch.object(engine, '_load_required_skills', return_value={}):
                        with patch.object(engine, '_load_modifiers', return_value=[]):
                            with patch.object(engine, '_load_ship_effects', return_value=[]):
                                with patch.object(engine, '_get_all_skill_type_ids', return_value=set()):
                                    result_ship, result_mods, charge_bonuses, modified_charges = (
                                        engine.calculate_modified_attributes(
                                            ship_type_id=ship_type_id,
                                            fitted_module_type_ids=[],
                                            skill_levels={},
                                        )
                                    )

        # Ship attrs should be unchanged (no modules, no skills, no role bonuses)
        assert result_ship[263] == pytest.approx(5000.0)
        assert result_ship[265] == pytest.approx(3000.0)
        assert result_ship[9] == pytest.approx(2000.0)
        assert result_ship[48] == pytest.approx(300.0)
        assert result_ship[11] == pytest.approx(1000.0)

        # No modules fitted → empty module attrs
        assert result_mods == {}

        # No ship role bonuses → empty charge bonuses
        assert charge_bonuses == []

        # No charges → empty modified charges
        assert modified_charges == {}

    def test_return_tuple_has_four_elements(self):
        """Verify the pipeline returns a 4-tuple."""
        engine = DogmaEngine.__new__(DogmaEngine)
        engine.db = MagicMock()

        with patch.object(engine, '_load_all_attributes', return_value={99999: {}}):
            with patch.object(engine, '_supplement_invtypes_attrs', side_effect=lambda tid, a: a):
                with patch.object(engine, '_load_group_ids', return_value={}):
                    with patch.object(engine, '_load_required_skills', return_value={}):
                        with patch.object(engine, '_load_modifiers', return_value=[]):
                            with patch.object(engine, '_load_ship_effects', return_value=[]):
                                with patch.object(engine, '_get_all_skill_type_ids', return_value=set()):
                                    result = engine.calculate_modified_attributes(
                                        ship_type_id=99999,
                                        fitted_module_type_ids=[],
                                        skill_levels={},
                                    )

        assert isinstance(result, tuple)
        assert len(result) == 4
        ship_attrs, mod_attrs, charge_bonuses, modified_charges = result
        assert isinstance(ship_attrs, dict)
        assert isinstance(mod_attrs, dict)
        assert isinstance(charge_bonuses, list)
        assert isinstance(modified_charges, dict)

    def test_signature_accepts_all_params(self):
        """Verify calculate_modified_attributes accepts all documented parameters."""
        import inspect
        sig = inspect.signature(DogmaEngine.calculate_modified_attributes)
        params = list(sig.parameters.keys())
        assert 'ship_type_id' in params
        assert 'fitted_module_type_ids' in params
        assert 'skill_levels' in params
        assert 'implant_type_ids' in params
        assert 'module_flags' in params
        assert 'flag_states' in params
        assert 'booster_type_ids' in params
        assert 'mode_type_id' in params
        assert 'charge_type_ids' in params
        assert 'simulation_mode' in params
