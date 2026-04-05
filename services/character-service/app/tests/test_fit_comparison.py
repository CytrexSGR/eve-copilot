# test_fit_comparison.py
"""Tests for fit comparison endpoint."""
import pytest
from pydantic import BaseModel, ValidationError
from typing import List
from app.services.fitting_stats.models import FittingStatsRequest
from app.services.fitting_service import FittingItem


class TestCompareRequest:
    def test_comparison_accepts_two_fittings(self):
        """CompareRequest accepts a list of 2 fittings."""
        from app.routers.fittings import CompareRequest
        req = CompareRequest(fittings=[
            FittingStatsRequest(ship_type_id=24698, items=[]),
            FittingStatsRequest(ship_type_id=24690, items=[]),
        ])
        assert len(req.fittings) == 2

    def test_comparison_accepts_four_fittings(self):
        from app.routers.fittings import CompareRequest
        req = CompareRequest(fittings=[
            FittingStatsRequest(ship_type_id=24698, items=[]),
            FittingStatsRequest(ship_type_id=24690, items=[]),
            FittingStatsRequest(ship_type_id=17720, items=[]),
            FittingStatsRequest(ship_type_id=17726, items=[]),
        ])
        assert len(req.fittings) == 4

    def test_comparison_preserves_module_states(self):
        """Each fitting in comparison can have its own module states."""
        from app.routers.fittings import CompareRequest
        req = CompareRequest(fittings=[
            FittingStatsRequest(
                ship_type_id=24698,
                items=[FittingItem(type_id=3170, flag=19, quantity=1)],
                module_states={19: "overheated"},
            ),
            FittingStatsRequest(
                ship_type_id=24698,
                items=[FittingItem(type_id=3170, flag=19, quantity=1)],
                module_states={19: "active"},
            ),
        ])
        assert req.fittings[0].module_states == {19: "overheated"}
        assert req.fittings[1].module_states == {19: "active"}

    def test_comparison_fittings_list_type(self):
        from app.routers.fittings import CompareRequest
        req = CompareRequest(fittings=[
            FittingStatsRequest(ship_type_id=24698, items=[]),
            FittingStatsRequest(ship_type_id=24690, items=[]),
        ])
        assert isinstance(req.fittings, list)
        assert all(isinstance(f, FittingStatsRequest) for f in req.fittings)

    def test_single_fitting_validation(self):
        """CompareRequest with only 1 fitting should still be valid at model level."""
        from app.routers.fittings import CompareRequest
        req = CompareRequest(fittings=[
            FittingStatsRequest(ship_type_id=24698, items=[]),
        ])
        # Model accepts it -- the 2-4 check happens in the endpoint logic
        assert len(req.fittings) == 1

    def test_comparison_with_boosters(self):
        """Each fitting can have its own boosters."""
        from app.routers.fittings import CompareRequest
        from app.services.fitting_stats.models import BoosterInput
        req = CompareRequest(fittings=[
            FittingStatsRequest(
                ship_type_id=24698, items=[],
                boosters=[BoosterInput(type_id=28672, side_effects_enabled=[])],
            ),
            FittingStatsRequest(ship_type_id=24698, items=[]),
        ])
        assert len(req.fittings[0].boosters) == 1
        assert req.fittings[1].boosters is None
