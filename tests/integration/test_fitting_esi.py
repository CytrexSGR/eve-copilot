# tests/integration/test_fitting_esi.py
"""Integration tests for ESI fittings."""

import pytest
from src.services.fitting.service import FittingService


@pytest.mark.integration
class TestFittingESI:
    """Integration tests for ESI fittings endpoint."""

    def test_get_character_fittings(self):
        """Test fetching fittings from ESI for Cytrex."""
        service = FittingService()

        fittings = service.get_character_fittings(1117367444)  # Cytrex

        # Should return a list (may be empty if no saved fittings)
        assert isinstance(fittings, list)

    def test_get_character_fittings_returns_esi_fitting_objects(self):
        """Test that fittings are properly parsed into ESIFitting objects."""
        service = FittingService()

        fittings = service.get_character_fittings(1117367444)  # Cytrex

        if fittings:
            # Verify the first fitting has the expected structure
            fitting = fittings[0]
            assert hasattr(fitting, 'fitting_id')
            assert hasattr(fitting, 'name')
            assert hasattr(fitting, 'ship_type_id')
            assert hasattr(fitting, 'items')
            assert isinstance(fitting.fitting_id, int)
            assert isinstance(fitting.name, str)
            assert isinstance(fitting.ship_type_id, int)
            assert isinstance(fitting.items, list)

    def test_get_character_fittings_invalid_character(self):
        """Test handling of invalid character ID."""
        service = FittingService()

        # Should return empty list for invalid character (graceful handling)
        fittings = service.get_character_fittings(999999999)

        assert isinstance(fittings, list)
        assert len(fittings) == 0

    def test_analyze_character_fitting_by_id(self):
        """Test analyzing a specific fitting by ID."""
        service = FittingService()

        # First get the list of fittings
        fittings = service.get_character_fittings(1117367444)

        if fittings:
            # Analyze the first fitting
            result = service.analyze_fitting_by_id(
                character_id=1117367444,
                fitting_id=fittings[0].fitting_id,
                ammo_type_id=27353,  # Fury Cruise Missile (default)
            )

            assert result is not None
            assert result.total_dps >= 0

    def test_analyze_fitting_by_id_not_found(self):
        """Test that non-existent fitting ID returns None."""
        service = FittingService()

        result = service.analyze_fitting_by_id(
            character_id=1117367444,
            fitting_id=999999999,  # Non-existent fitting
            ammo_type_id=27353,
        )

        assert result is None

    def test_analyze_fitting_by_id_with_active_modules(self):
        """Test analyzing fitting with active modules specified."""
        service = FittingService()

        fittings = service.get_character_fittings(1117367444)

        if fittings:
            # Analyze with empty active modules (Bastion off)
            result = service.analyze_fitting_by_id(
                character_id=1117367444,
                fitting_id=fittings[0].fitting_id,
                ammo_type_id=27353,
                active_modules=[],
            )

            assert result is not None
            assert result.bastion_multiplier == 1.0  # No bastion active
