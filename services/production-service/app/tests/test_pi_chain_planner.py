"""Tests for ChainPlannerService (PI chain planner).

Target: ~20+ tests covering plan CRUD, target tree walking,
node assignment, and IST/SOLL status check.
"""

import pytest
from contextlib import contextmanager
from datetime import datetime, timezone

from app.services.pi.chain_planner import ChainPlannerService
from app.services.pi.models import PIChainNode


# -- Mock Infrastructure --------------------------------------------------

NOW = datetime(2026, 2, 18, 12, 0, 0, tzinfo=timezone.utc)


class MultiResultCursor:
    """Mock cursor returning successive result sets per execute() call."""

    def __init__(self, results_sequence):
        self._results = list(results_sequence)
        self._idx = 0
        self.executed = []
        self.rowcount = 1

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        result = self._results[self._idx] if self._idx < len(self._results) else []
        self._idx += 1
        return result

    def fetchone(self):
        result = self._results[self._idx] if self._idx < len(self._results) else None
        if isinstance(result, list):
            result = result[0] if result else None
        self._idx += 1
        return result


class MockDB:
    """Mock database pool with cursor() context manager."""

    def __init__(self, cursor):
        self._cursor = cursor

    @contextmanager
    def cursor(self, **kwargs):
        yield self._cursor


# -- Helpers ---------------------------------------------------------------

def _make_plan(id=1, name="Test Plan", status="planning"):
    return {
        "id": id,
        "name": name,
        "status": status,
        "created_at": NOW,
        "updated_at": NOW,
    }


def _make_node(
    id=1, plan_id=1, type_id=2393, type_name="Livestock",
    tier=1, is_target=False, soll_qty_per_hour=40.0,
    character_id=None, planet_id=None,
):
    return {
        "id": id,
        "plan_id": plan_id,
        "type_id": type_id,
        "type_name": type_name,
        "tier": tier,
        "is_target": is_target,
        "soll_qty_per_hour": soll_qty_per_hour,
        "character_id": character_id,
        "planet_id": planet_id,
    }


def _make_edge(id=1, plan_id=1, source_node_id=2, target_node_id=1, quantity_ratio=40.0):
    return {
        "id": id,
        "plan_id": plan_id,
        "source_node_id": source_node_id,
        "target_node_id": target_node_id,
        "quantity_ratio": quantity_ratio,
    }


def _p0_chain(type_id=2268, type_name="Proteins", quantity=40.0):
    """Single P0 leaf node."""
    return PIChainNode(
        type_id=type_id,
        type_name=type_name,
        tier=0,
        quantity_needed=quantity,
    )


def _p1_chain():
    """P1 product (Livestock) from 2 P0 materials."""
    return PIChainNode(
        type_id=2393,
        type_name="Livestock",
        tier=1,
        quantity_needed=5.0,
        schematic_id=121,
        children=[
            _p0_chain(type_id=2268, type_name="Proteins", quantity=40.0),
            _p0_chain(type_id=2073, type_name="Biofuels", quantity=40.0),
        ],
    )


def _p2_chain():
    """P2 product from 2 P1 products, each with 2 P0 inputs = 5 nodes, 4 edges."""
    return PIChainNode(
        type_id=2399,
        type_name="Ukomi Superconductors",
        tier=2,
        quantity_needed=3.0,
        schematic_id=130,
        children=[
            PIChainNode(
                type_id=2393,
                type_name="Livestock",
                tier=1,
                quantity_needed=10.0,
                schematic_id=121,
                children=[
                    _p0_chain(type_id=2268, type_name="Proteins", quantity=40.0),
                    _p0_chain(type_id=2073, type_name="Biofuels", quantity=40.0),
                ],
            ),
            PIChainNode(
                type_id=2396,
                type_name="Biocells",
                tier=1,
                quantity_needed=10.0,
                schematic_id=122,
                children=[
                    _p0_chain(type_id=2073, type_name="Biofuels", quantity=40.0),
                    _p0_chain(type_id=2286, type_name="Precious Metals", quantity=40.0),
                ],
            ),
        ],
    )


# ==========================================================================
# TestCreatePlan
# ==========================================================================


class TestCreatePlan:
    """Tests for ChainPlannerService.create_plan()."""

    def test_creates_plan_and_returns_dict(self):
        plan = _make_plan(id=42, name="My PI Plan")
        cursor = MultiResultCursor([[plan]])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.create_plan("My PI Plan")

        assert result["id"] == 42
        assert result["name"] == "My PI Plan"
        assert result["status"] == "planning"
        sql = cursor.executed[0][0]
        assert "INSERT INTO pi_plans" in sql
        assert cursor.executed[0][1] == ("My PI Plan",)

    def test_create_plan_sql_contains_returning(self):
        cursor = MultiResultCursor([[_make_plan()]])
        svc = ChainPlannerService(MockDB(cursor))

        svc.create_plan("X")

        sql = cursor.executed[0][0]
        assert "RETURNING" in sql


# ==========================================================================
# TestGetPlan
# ==========================================================================


class TestGetPlan:
    """Tests for ChainPlannerService.get_plan()."""

    def test_returns_plan_with_nodes_and_edges(self):
        plan = _make_plan(id=1)
        nodes = [_make_node(id=1, is_target=True), _make_node(id=2, type_id=2268)]
        edges = [_make_edge(id=1, source_node_id=2, target_node_id=1)]
        cursor = MultiResultCursor([
            [plan],   # plan query
            nodes,    # nodes query
            edges,    # edges query
        ])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.get_plan(plan_id=1)

        assert result is not None
        assert result["id"] == 1
        assert result["name"] == "Test Plan"
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        assert result["nodes"][0]["is_target"] is True

    def test_returns_none_for_nonexistent_plan(self):
        cursor = MultiResultCursor([
            [],  # plan not found
        ])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.get_plan(plan_id=999)

        assert result is None
        # Should only execute the plan query, not nodes/edges
        assert len(cursor.executed) == 1


# ==========================================================================
# TestListPlans
# ==========================================================================


class TestListPlans:
    """Tests for ChainPlannerService.list_plans()."""

    def test_list_all_plans(self):
        plans = [_make_plan(id=1), _make_plan(id=2, name="Plan B")]
        cursor = MultiResultCursor([plans])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.list_plans()

        assert len(result) == 2
        sql = cursor.executed[0][0]
        assert "LEFT JOIN pi_plan_nodes" in sql
        assert "GROUP BY p.id" in sql
        assert "WHERE p.status" not in sql

    def test_list_plans_filtered_by_status(self):
        plans = [_make_plan(id=1, status="active")]
        cursor = MultiResultCursor([plans])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.list_plans(status="active")

        assert len(result) == 1
        sql = cursor.executed[0][0]
        assert "WHERE p.status = %s" in sql
        assert cursor.executed[0][1] == ("active",)

    def test_list_plans_empty(self):
        cursor = MultiResultCursor([[]])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.list_plans()

        assert result == []


# ==========================================================================
# TestDeletePlan
# ==========================================================================


class TestDeletePlan:
    """Tests for ChainPlannerService.delete_plan()."""

    def test_returns_true_on_success(self):
        cursor = MultiResultCursor([[{"id": 1}]])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.delete_plan(plan_id=1)

        assert result is True
        sql = cursor.executed[0][0]
        assert "DELETE FROM pi_plans" in sql
        assert cursor.executed[0][1] == (1,)

    def test_returns_false_when_not_found(self):
        cursor = MultiResultCursor([[]])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.delete_plan(plan_id=999)

        assert result is False


# ==========================================================================
# TestUpdatePlanStatus
# ==========================================================================


class TestUpdatePlanStatus:
    """Tests for ChainPlannerService.update_plan_status()."""

    def test_updates_status_successfully(self):
        cursor = MultiResultCursor([[{"id": 1}]])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.update_plan_status(plan_id=1, status="active")

        assert result is True
        sql = cursor.executed[0][0]
        assert "UPDATE pi_plans" in sql
        assert "SET status = %s" in sql
        assert cursor.executed[0][1] == ("active", 1)

    def test_returns_false_when_plan_not_found(self):
        cursor = MultiResultCursor([[]])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.update_plan_status(plan_id=999, status="active")

        assert result is False

    def test_raises_on_invalid_status(self):
        cursor = MultiResultCursor([])
        svc = ChainPlannerService(MockDB(cursor))

        with pytest.raises(ValueError, match="Invalid status"):
            svc.update_plan_status(plan_id=1, status="invalid")


# ==========================================================================
# TestAddTarget
# ==========================================================================


class TestAddTarget:
    """Tests for ChainPlannerService.add_target() tree walking."""

    def test_single_p1_creates_3_nodes_2_edges(self):
        """P1 Livestock (tier 1) has 2 P0 children -> 3 nodes, 2 edges.

        Only node INSERT calls fetchone(); edge INSERT only calls execute().
        So result sets correspond only to fetchone() calls (node inserts).
        """
        chain = _p1_chain()
        # DFS walk: Livestock (root) -> Proteins (child+edge) -> Biofuels (child+edge)
        # fetchone() is called 3 times (once per node upsert)
        cursor = MultiResultCursor([
            [{"id": 10, "was_inserted": True}],   # Livestock
            [{"id": 11, "was_inserted": True}],   # Proteins
            [{"id": 12, "was_inserted": True}],   # Biofuels
        ])
        svc = ChainPlannerService(MockDB(cursor))

        stats = svc.add_target(plan_id=1, chain=chain)

        assert stats["nodes_created"] == 3
        assert stats["nodes_merged"] == 0
        assert stats["edges_created"] == 2

    def test_shared_intermediate_merges_node(self):
        """When a node with same type_id already exists, it merges (soll_qty sums)."""
        chain = _p1_chain()
        # fetchone() is called 3 times (once per node upsert)
        cursor = MultiResultCursor([
            [{"id": 10, "was_inserted": False}],   # Livestock (merged)
            [{"id": 11, "was_inserted": True}],    # Proteins
            [{"id": 12, "was_inserted": True}],    # Biofuels
        ])
        svc = ChainPlannerService(MockDB(cursor))

        stats = svc.add_target(plan_id=1, chain=chain)

        assert stats["nodes_created"] == 2
        assert stats["nodes_merged"] == 1
        assert stats["edges_created"] == 2

    def test_p2_chain_creates_nodes_and_edges(self):
        """P2 -> 2 P1 -> 4 P0 (Biofuels shared between two P1s).

        DFS walk visits 7 nodes total (P2, P1a, P0-Proteins, P0-Biofuels,
        P1b, P0-Biofuels-again, P0-PreciousMetals).
        Edges: 6 (each non-root node creates one edge to its parent).
        Only node upserts call fetchone(), so 7 result sets needed.
        """
        chain = _p2_chain()
        cursor = MultiResultCursor([
            [{"id": 20, "was_inserted": True}],    # P2 (root)
            [{"id": 21, "was_inserted": True}],    # P1a Livestock
            [{"id": 22, "was_inserted": True}],    # P0 Proteins
            [{"id": 23, "was_inserted": True}],    # P0 Biofuels
            [{"id": 24, "was_inserted": True}],    # P1b Biocells
            [{"id": 25, "was_inserted": False}],   # P0 Biofuels (merge!)
            [{"id": 26, "was_inserted": True}],    # P0 Precious Metals
        ])
        svc = ChainPlannerService(MockDB(cursor))

        stats = svc.add_target(plan_id=1, chain=chain)

        assert stats["nodes_created"] == 6
        assert stats["nodes_merged"] == 1  # Biofuels shared between P1a and P1b
        assert stats["edges_created"] == 6

    def test_root_node_is_target(self):
        """The root node should have is_target=True."""
        chain = PIChainNode(
            type_id=2393, type_name="Livestock", tier=1,
            quantity_needed=5.0, schematic_id=121, children=[],
        )
        cursor = MultiResultCursor([
            [{"id": 1, "was_inserted": True}],
        ])
        svc = ChainPlannerService(MockDB(cursor))

        svc.add_target(plan_id=1, chain=chain)

        # Verify the INSERT params include is_target=True for root
        sql, params = cursor.executed[0]
        assert "INSERT INTO pi_plan_nodes" in sql
        # params: (plan_id, type_id, type_name, tier, is_target, soll_qty)
        assert params[4] is True  # is_target


# ==========================================================================
# TestAssignNode
# ==========================================================================


class TestAssignNode:
    """Tests for ChainPlannerService.assign_node()."""

    def test_assigns_character_and_planet(self):
        updated_node = _make_node(id=5, character_id=123, planet_id=40000001)
        cursor = MultiResultCursor([[updated_node]])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.assign_node(plan_id=1, node_id=5, character_id=123, planet_id=40000001)

        assert result is not None
        assert result["character_id"] == 123
        assert result["planet_id"] == 40000001
        sql = cursor.executed[0][0]
        assert "UPDATE pi_plan_nodes" in sql
        assert "AND plan_id = %s" in sql
        assert cursor.executed[0][1] == (123, 40000001, 5, 1)

    def test_returns_none_when_node_not_found(self):
        cursor = MultiResultCursor([[]])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.assign_node(plan_id=1, node_id=999, character_id=123, planet_id=40000001)

        assert result is None


# ==========================================================================
# TestRemoveTarget
# ==========================================================================


class TestRemoveTarget:
    """Tests for ChainPlannerService.remove_target()."""

    def test_deletes_all_edges_then_nodes(self):
        cursor = MultiResultCursor([
            [],  # DELETE edges (fetchall not called, but cursor advances on execute)
            [],  # DELETE nodes
        ])
        # Override: remove_target only calls execute, no fetch
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.remove_target(plan_id=1)

        assert result == []
        assert len(cursor.executed) == 2
        assert "DELETE FROM pi_plan_edges" in cursor.executed[0][0]
        assert "DELETE FROM pi_plan_nodes" in cursor.executed[1][0]


# ==========================================================================
# TestStatusCheck
# ==========================================================================


class TestStatusCheck:
    """Tests for ChainPlannerService.get_status_check()."""

    def test_unassigned_node_status(self):
        """Nodes without character_id/planet_id get status 'unassigned'."""
        nodes = [_make_node(id=1, soll_qty_per_hour=40.0, character_id=None, planet_id=None)]
        cursor = MultiResultCursor([
            nodes,  # SELECT nodes
            # No pi_pins query for unassigned nodes
        ])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.get_status_check(plan_id=1)

        assert len(result) == 1
        assert result[0]["status"] == "unassigned"
        assert result[0]["ist_qty_per_hour"] == 0
        assert result[0]["delta_percent"] == -100.0

    def test_matched_status_ok(self):
        """IST >= 90% SOLL -> status 'ok'."""
        nodes = [_make_node(
            id=1, type_id=2393, soll_qty_per_hour=40.0,
            character_id=123, planet_id=40000001,
        )]
        # pi_pins returns IST = 38 (95% of SOLL 40)
        pin_result = [{"ist_qty_per_hour": 38.0}]
        cursor = MultiResultCursor([
            nodes,       # SELECT nodes
            pin_result,  # SUM from pi_pins
        ])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.get_status_check(plan_id=1)

        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["ist_qty_per_hour"] == 38.0
        assert result[0]["delta_percent"] == -5.0

    def test_warning_status(self):
        """IST between 50% and 90% of SOLL -> status 'warning'."""
        nodes = [_make_node(
            id=1, type_id=2393, soll_qty_per_hour=100.0,
            character_id=123, planet_id=40000001,
        )]
        pin_result = [{"ist_qty_per_hour": 60.0}]
        cursor = MultiResultCursor([
            nodes,
            pin_result,
        ])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.get_status_check(plan_id=1)

        assert result[0]["status"] == "warning"
        assert result[0]["ist_qty_per_hour"] == 60.0
        assert result[0]["delta_percent"] == -40.0

    def test_critical_status(self):
        """IST < 50% SOLL -> status 'critical'."""
        nodes = [_make_node(
            id=1, type_id=2393, soll_qty_per_hour=100.0,
            character_id=123, planet_id=40000001,
        )]
        pin_result = [{"ist_qty_per_hour": 20.0}]
        cursor = MultiResultCursor([
            nodes,
            pin_result,
        ])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.get_status_check(plan_id=1)

        assert result[0]["status"] == "critical"
        assert result[0]["ist_qty_per_hour"] == 20.0
        assert result[0]["delta_percent"] == -80.0

    def test_mixed_statuses_multiple_nodes(self):
        """Multiple nodes with different IST/SOLL ratios."""
        nodes = [
            _make_node(id=1, type_id=2393, soll_qty_per_hour=40.0,
                       character_id=123, planet_id=40000001),
            _make_node(id=2, type_id=2268, soll_qty_per_hour=100.0,
                       character_id=None, planet_id=None),
            _make_node(id=3, type_id=2073, soll_qty_per_hour=80.0,
                       character_id=456, planet_id=40000002),
        ]
        cursor = MultiResultCursor([
            nodes,
            # Node 1: IST=36 (90% -> ok)
            [{"ist_qty_per_hour": 36.0}],
            # Node 2: unassigned (skipped in pi_pins query)
            # Node 3: IST=30 (37.5% -> critical)
            [{"ist_qty_per_hour": 30.0}],
        ])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.get_status_check(plan_id=1)

        assert len(result) == 3
        assert result[0]["status"] == "ok"
        assert result[1]["status"] == "unassigned"
        assert result[2]["status"] == "critical"

    def test_zero_soll_does_not_divide_by_zero(self):
        """When SOLL is 0, should not crash."""
        nodes = [_make_node(
            id=1, type_id=2393, soll_qty_per_hour=0,
            character_id=123, planet_id=40000001,
        )]
        pin_result = [{"ist_qty_per_hour": 5.0}]
        cursor = MultiResultCursor([
            nodes,
            pin_result,
        ])
        svc = ChainPlannerService(MockDB(cursor))

        result = svc.get_status_check(plan_id=1)

        assert len(result) == 1
        # With SOLL=0 and IST=5, ratio=1.0 -> ok
        assert result[0]["status"] == "ok"
        assert result[0]["delta_percent"] == 0.0
