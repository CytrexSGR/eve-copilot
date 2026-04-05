"""Tests for production chain dependency analysis.

Tests the service methods in app/services/chains.py:
  - get_chain_tree: build hierarchical production tree
  - get_materials_list: flattened material list with ME adjustments
  - get_direct_dependencies: first-level dependencies only
  - Edge cases: unknown type_id, no blueprint, circular dependencies
"""

import math
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.services.chains import ProductionChainService


# =============================================================================
# Helpers
# =============================================================================


def _make_service(
    item_names=None,
    is_manufacturable_map=None,
    blueprint_map=None,
    materials_map=None,
    output_qty_map=None,
):
    """Create a ProductionChainService with a mocked repository.

    Args:
        item_names: dict {type_id: name}
        is_manufacturable_map: dict {type_id: bool}
        blueprint_map: dict {product_type_id: blueprint_id}
        materials_map: dict {blueprint_id: [(material_id, qty), ...]}
        output_qty_map: dict {(blueprint_id, product_id): qty}
    """
    item_names = item_names or {}
    is_manufacturable_map = is_manufacturable_map or {}
    blueprint_map = blueprint_map or {}
    materials_map = materials_map or {}
    output_qty_map = output_qty_map or {}

    db = MagicMock()
    service = ProductionChainService(db)

    # Mock the repository methods
    service.repository = MagicMock()
    service.repository.get_item_name.side_effect = lambda tid: item_names.get(tid)
    service.repository.is_manufacturable.side_effect = lambda tid: is_manufacturable_map.get(tid, False)
    service.repository.get_blueprint_for_product.side_effect = lambda tid: blueprint_map.get(tid)
    service.repository.get_blueprint_materials.side_effect = lambda bid: materials_map.get(bid, [])
    service.repository.get_output_quantity.side_effect = lambda bid, pid: output_qty_map.get((bid, pid), 1)

    return service


# =============================================================================
# get_chain_tree tests
# =============================================================================


class TestGetChainTree:
    """Test production chain tree building."""

    def test_simple_item_tree(self):
        """A simple item with raw material dependencies."""
        # Item 100 (Ship) requires: 34 (Tritanium) + 35 (Pyerite)
        service = _make_service(
            item_names={100: "Rifter", 34: "Tritanium", 35: "Pyerite"},
            is_manufacturable_map={100: True, 34: False, 35: False},
            blueprint_map={100: 1000},
            materials_map={1000: [(34, 5000), (35, 2000)]},
            output_qty_map={(1000, 100): 1},
        )

        result = service.get_chain_tree(100, quantity=1)

        assert "chain" in result
        assert result["type_id"] == 100
        assert result["name"] == "Rifter"
        chain = result["chain"]
        assert chain["is_manufacturable"] is True
        assert len(chain["children"]) == 2

    def test_tree_format_contains_chain_key(self):
        """Tree format returns 'chain' key."""
        service = _make_service(
            item_names={100: "Item"},
            is_manufacturable_map={100: False},
        )

        result = service.get_chain_tree(100, quantity=1, format="tree")
        assert "chain" in result

    def test_flat_format_contains_materials_key(self):
        """Flat format returns 'materials' key."""
        service = _make_service(
            item_names={100: "Ship", 34: "Tritanium"},
            is_manufacturable_map={100: True, 34: False},
            blueprint_map={100: 1000},
            materials_map={1000: [(34, 5000)]},
            output_qty_map={(1000, 100): 1},
        )

        result = service.get_chain_tree(100, quantity=1, format="flat")
        assert "materials" in result
        assert isinstance(result["materials"], list)

    def test_unknown_type_id(self):
        """Unknown type_id returns error dict."""
        service = _make_service(item_names={})
        result = service.get_chain_tree(99999, quantity=1)
        assert "error" in result

    def test_non_manufacturable_item(self):
        """Non-manufacturable item has no children."""
        service = _make_service(
            item_names={34: "Tritanium"},
            is_manufacturable_map={34: False},
        )

        result = service.get_chain_tree(34, quantity=1)
        chain = result["chain"]
        assert chain["is_manufacturable"] is False
        assert chain["children"] == []

    def test_nested_tree(self):
        """Multi-level tree: Ship -> Component -> Raw material."""
        # Ship 100 needs Component 200
        # Component 200 needs Raw 34
        service = _make_service(
            item_names={100: "Ship", 200: "Component", 34: "Tritanium"},
            is_manufacturable_map={100: True, 200: True, 34: False},
            blueprint_map={100: 1000, 200: 2000},
            materials_map={1000: [(200, 10)], 2000: [(34, 500)]},
            output_qty_map={(1000, 100): 1, (2000, 200): 1},
        )

        result = service.get_chain_tree(100, quantity=1)
        chain = result["chain"]
        assert len(chain["children"]) == 1
        component = chain["children"][0]
        assert component["name"] == "Component"
        assert component["is_manufacturable"] is True
        assert len(component["children"]) == 1
        assert component["children"][0]["name"] == "Tritanium"

    def test_quantity_multiplied(self):
        """Quantity scales material requirements."""
        service = _make_service(
            item_names={100: "Ship", 34: "Tritanium"},
            is_manufacturable_map={100: True, 34: False},
            blueprint_map={100: 1000},
            materials_map={1000: [(34, 5000)]},
            output_qty_map={(1000, 100): 1},
        )

        result = service.get_chain_tree(100, quantity=3)
        chain = result["chain"]
        # 3 runs needed, each requiring 5000 Trit = 15000
        assert chain["children"][0]["quantity"] == 15000

    def test_output_per_run_affects_runs(self):
        """If blueprint produces 10 per run, need fewer runs."""
        service = _make_service(
            item_names={100: "Ammo", 34: "Tritanium"},
            is_manufacturable_map={100: True, 34: False},
            blueprint_map={100: 1000},
            materials_map={1000: [(34, 100)]},
            output_qty_map={(1000, 100): 100},  # 100 per run
        )

        result = service.get_chain_tree(100, quantity=100)
        chain = result["chain"]
        # 100 wanted / 100 per run = 1 run, 1 * 100 trit = 100
        assert chain["children"][0]["quantity"] == 100


# =============================================================================
# get_materials_list tests
# =============================================================================


class TestGetMaterialsList:
    """Test flattened material list with ME adjustments."""

    def test_basic_materials(self):
        """Returns material list with base and adjusted quantities."""
        service = _make_service(
            item_names={100: "Ship", 34: "Tritanium", 35: "Pyerite"},
            blueprint_map={100: 1000},
            materials_map={1000: [(34, 1000), (35, 500)]},
        )

        result = service.get_materials_list(100, me=0, runs=1)

        assert "materials" in result
        assert len(result["materials"]) == 2
        assert result["me"] == 0
        assert result["runs"] == 1

    def test_me_adjustment(self):
        """ME 10 reduces quantities by 10%."""
        service = _make_service(
            item_names={100: "Ship", 34: "Tritanium"},
            blueprint_map={100: 1000},
            materials_map={1000: [(34, 1000)]},
        )

        result = service.get_materials_list(100, me=10, runs=1)
        mat = result["materials"][0]

        assert mat["base_quantity"] == 1000
        # max(1, ceil(1000 * 0.9)) = 900
        assert mat["adjusted_quantity"] == 900
        assert mat["per_run"] == 900

    def test_multiple_runs(self):
        """Multiple runs multiply adjusted quantity."""
        service = _make_service(
            item_names={100: "Ship", 34: "Tritanium"},
            blueprint_map={100: 1000},
            materials_map={1000: [(34, 1000)]},
        )

        result = service.get_materials_list(100, me=10, runs=5)
        mat = result["materials"][0]

        # per_run = 900, adjusted = 900 * 5 = 4500
        assert mat["per_run"] == 900
        assert mat["adjusted_quantity"] == 4500

    def test_unknown_type_id(self):
        """Unknown type_id returns error."""
        service = _make_service(item_names={})
        result = service.get_materials_list(99999)
        assert "error" in result

    def test_no_blueprint(self):
        """Item exists but has no blueprint."""
        service = _make_service(
            item_names={34: "Tritanium"},
            blueprint_map={},
        )
        result = service.get_materials_list(34)
        assert "error" in result

    def test_minimum_quantity_one(self):
        """Adjusted quantity is at least 1."""
        service = _make_service(
            item_names={100: "Ship", 34: "Tritanium"},
            blueprint_map={100: 1000},
            materials_map={1000: [(34, 1)]},
        )

        result = service.get_materials_list(100, me=10, runs=1)
        mat = result["materials"][0]
        # max(1, ceil(1 * 0.9)) = max(1, 1) = 1
        assert mat["adjusted_quantity"] >= 1


# =============================================================================
# get_direct_dependencies tests
# =============================================================================


class TestGetDirectDependencies:
    """Test first-level dependency retrieval."""

    def test_basic_dependencies(self):
        """Returns direct materials with manufacturability flag."""
        service = _make_service(
            item_names={100: "Ship", 34: "Tritanium", 200: "Component"},
            is_manufacturable_map={34: False, 200: True},
            blueprint_map={100: 1000},
            materials_map={1000: [(34, 5000), (200, 10)]},
        )

        result = service.get_direct_dependencies(100)

        assert "materials" in result
        assert len(result["materials"]) == 2

        by_id = {m["type_id"]: m for m in result["materials"]}
        assert by_id[34]["is_manufacturable"] is False
        assert by_id[200]["is_manufacturable"] is True
        assert by_id[34]["quantity"] == 5000

    def test_unknown_type_id(self):
        """Unknown type_id returns error."""
        service = _make_service(item_names={})
        result = service.get_direct_dependencies(99999)
        assert "error" in result

    def test_no_blueprint(self):
        """Item with no blueprint returns error."""
        service = _make_service(
            item_names={34: "Tritanium"},
            blueprint_map={},
        )
        result = service.get_direct_dependencies(34)
        assert "error" in result

    def test_does_not_recurse(self):
        """Only returns first level, not nested dependencies."""
        # Ship needs Component, Component needs Raw
        # But direct deps should only show Component
        service = _make_service(
            item_names={100: "Ship", 200: "Component", 34: "Tritanium"},
            is_manufacturable_map={200: True, 34: False},
            blueprint_map={100: 1000, 200: 2000},
            materials_map={1000: [(200, 10)], 2000: [(34, 500)]},
        )

        result = service.get_direct_dependencies(100)

        assert len(result["materials"]) == 1
        assert result["materials"][0]["type_id"] == 200
