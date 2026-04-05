"""Tests for arbitrage route items JOIN optimization."""
import pytest


def test_group_items_by_route_basic():
    from app.routers.arbitrage import _group_items_by_route
    rows = [
        {"route_id": 1, "type_id": 100, "type_name": "Trit"},
        {"route_id": 1, "type_id": 101, "type_name": "Pye"},
        {"route_id": 2, "type_id": 200, "type_name": "Mex"},
    ]
    grouped = _group_items_by_route(rows)
    assert len(grouped[1]) == 2
    assert len(grouped[2]) == 1


def test_group_items_by_route_empty():
    from app.routers.arbitrage import _group_items_by_route
    assert _group_items_by_route([]) == {}


def test_group_items_by_route_preserves_order():
    from app.routers.arbitrage import _group_items_by_route
    rows = [
        {"route_id": 1, "type_id": 100, "type_name": "First"},
        {"route_id": 1, "type_id": 101, "type_name": "Second"},
    ]
    grouped = _group_items_by_route(rows)
    assert grouped[1][0]["type_name"] == "First"
    assert grouped[1][1]["type_name"] == "Second"


def test_group_items_missing_route():
    from app.routers.arbitrage import _group_items_by_route
    rows = [{"route_id": 5, "type_id": 1, "type_name": "X"}]
    grouped = _group_items_by_route(rows)
    # Route 99 not in results -> should return empty when accessed
    assert grouped.get(99, []) == []
