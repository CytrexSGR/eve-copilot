"""Tests for ProductionProjects ProjectService class."""

import pytest
from contextlib import contextmanager
from datetime import datetime, timezone

from app.services.project_service import ProjectService


# -- Mock Infrastructure --------------------------------------------------

class MultiResultCursor:
    """Mock cursor returning successive result sets per execute() call.

    Each call to fetchall / fetchone consumes the next result set in order.
    """

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

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockDB:
    """Mock database pool compatible with ProjectService.

    Supports ``self.db.cursor(cursor_factory=...)`` context manager pattern.
    """

    def __init__(self, cursor):
        self._cursor = cursor

    @contextmanager
    def cursor(self, **kwargs):
        yield self._cursor


# -- Helpers ---------------------------------------------------------------

NOW = datetime(2026, 2, 14, 12, 0, 0, tzinfo=timezone.utc)


def _make_project(
    id=1,
    creator_character_id=123,
    name="Test Project",
    description="A project",
    corporation_id=None,
    status="active",
    created_at=None,
    updated_at=None,
):
    return {
        "id": id,
        "creator_character_id": creator_character_id,
        "name": name,
        "description": description,
        "corporation_id": corporation_id,
        "status": status,
        "created_at": created_at or NOW,
        "updated_at": updated_at or NOW,
    }


def _make_item(
    id=1,
    project_id=1,
    type_id=24698,
    quantity=1,
    me_level=10,
    te_level=20,
    status="pending",
    added_at=None,
    type_name="Drake",
):
    item = {
        "id": id,
        "project_id": project_id,
        "type_id": type_id,
        "quantity": quantity,
        "me_level": me_level,
        "te_level": te_level,
        "status": status,
        "added_at": added_at or NOW,
    }
    if type_name is not None:
        item["type_name"] = type_name
    return item


def _make_decision(
    id=1,
    project_item_id=1,
    material_type_id=34,
    decision="buy",
    quantity=1000,
    type_name="Tritanium",
):
    return {
        "id": id,
        "project_item_id": project_item_id,
        "material_type_id": material_type_id,
        "decision": decision,
        "quantity": quantity,
        "type_name": type_name,
    }


# ==========================================================================
# TestListProjects
# ==========================================================================


class TestListProjects:
    """Tests for ProjectService.list_projects()."""

    def test_returns_projects_with_item_count(self):
        projects = [
            {**_make_project(id=1, name="Alpha"), "item_count": 3},
            {**_make_project(id=2, name="Beta"), "item_count": 0},
        ]
        cursor = MultiResultCursor([projects])
        svc = ProjectService(MockDB(cursor))

        result = svc.list_projects(character_id=123, corporation_id=456)

        assert len(result) == 2
        assert result[0]["name"] == "Alpha"
        assert result[0]["item_count"] == 3
        assert result[1]["item_count"] == 0
        # Verify query params
        assert cursor.executed[0][1] == (123, 456)

    def test_returns_empty_list_for_no_projects(self):
        cursor = MultiResultCursor([[]])
        svc = ProjectService(MockDB(cursor))

        result = svc.list_projects(character_id=999)

        assert result == []


# ==========================================================================
# TestCreateProject
# ==========================================================================


class TestCreateProject:
    """Tests for ProjectService.create_project()."""

    def test_creates_project_with_all_fields(self):
        project = _make_project(corporation_id=456)
        cursor = MultiResultCursor([
            [project],  # RETURNING *
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.create_project(
            creator_character_id=123,
            name="Test Project",
            description="A project",
            corporation_id=456,
        )

        assert result["name"] == "Test Project"
        assert result["corporation_id"] == 456
        sql, params = cursor.executed[0]
        assert "INSERT INTO production_projects" in sql
        assert params == (123, "Test Project", "A project", 456)

    def test_creates_personal_project_no_corporation(self):
        project = _make_project(corporation_id=None)
        cursor = MultiResultCursor([
            [project],
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.create_project(
            creator_character_id=123,
            name="Personal",
            description="Mine",
        )

        assert result["corporation_id"] is None
        _, params = cursor.executed[0]
        assert params == (123, "Personal", "Mine", None)


# ==========================================================================
# TestGetProject
# ==========================================================================


class TestGetProject:
    """Tests for ProjectService.get_project()."""

    def test_returns_project_with_items_and_type_name(self):
        project = _make_project(id=1)
        items = [
            {**_make_item(id=10, type_id=24698), "type_name": "Drake"},
            {**_make_item(id=11, type_id=17726), "type_name": "Apocalypse"},
        ]
        cursor = MultiResultCursor([
            [project],  # first execute: project
            items,       # second execute: items
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.get_project(project_id=1)

        assert result is not None
        assert result["name"] == "Test Project"
        assert len(result["items"]) == 2
        assert result["items"][0]["type_name"] == "Drake"
        assert result["items"][1]["type_name"] == "Apocalypse"

    def test_returns_none_for_nonexistent_project(self):
        cursor = MultiResultCursor([
            [],  # project not found
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.get_project(project_id=999)

        assert result is None
        # Should only execute the project lookup, not the items query
        assert len(cursor.executed) == 1


# ==========================================================================
# TestUpdateProject
# ==========================================================================


class TestUpdateProject:
    """Tests for ProjectService.update_project()."""

    def test_updates_name_only(self):
        updated = _make_project(id=1, name="Renamed")
        cursor = MultiResultCursor([
            [updated],  # RETURNING *
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.update_project(project_id=1, name="Renamed")

        assert result["name"] == "Renamed"
        sql, params = cursor.executed[0]
        assert "name = %s" in sql
        assert "updated_at = NOW()" in sql
        assert params == ["Renamed", 1]

    def test_updates_status(self):
        updated = _make_project(id=1, status="completed")
        cursor = MultiResultCursor([
            [updated],
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.update_project(project_id=1, status="completed")

        assert result["status"] == "completed"
        sql, params = cursor.executed[0]
        assert "status = %s" in sql

    def test_noop_returns_existing_project_when_no_fields(self):
        """When no valid kwargs are provided, get_project is called instead."""
        project = _make_project(id=5)
        items = [_make_item(id=20, project_id=5)]
        # get_project does 2 queries: project + items
        cursor = MultiResultCursor([
            [project],
            items,
        ])
        svc = ProjectService(MockDB(cursor))

        # Pass an invalid field that gets filtered out
        result = svc.update_project(project_id=5, invalid_field="ignored")

        assert result is not None
        assert result["id"] == 5
        # Should have done get_project (2 queries), not UPDATE
        assert "SELECT * FROM production_projects" in cursor.executed[0][0]


# ==========================================================================
# TestDeleteProject
# ==========================================================================


class TestDeleteProject:
    """Tests for ProjectService.delete_project()."""

    def test_returns_true_on_success(self):
        cursor = MultiResultCursor([
            [{"id": 1}],  # RETURNING id
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.delete_project(project_id=1)

        assert result is True
        sql, params = cursor.executed[0]
        assert "DELETE FROM production_projects" in sql
        assert params == (1,)

    def test_returns_false_when_not_found(self):
        cursor = MultiResultCursor([
            [],  # no row returned
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.delete_project(project_id=999)

        assert result is False


# ==========================================================================
# TestAddItem
# ==========================================================================


class TestAddItem:
    """Tests for ProjectService.add_item()."""

    def test_adds_item_with_type_name_resolved(self):
        item_row = _make_item(id=10, type_id=24698, quantity=5, me_level=10, te_level=20)
        # Remove type_name since it's added after resolution
        del item_row["type_name"]
        cursor = MultiResultCursor([
            [item_row],                      # INSERT RETURNING *
            [{"typeName": "Drake"}],         # type name lookup
            [],                               # UPDATE project updated_at (no result needed)
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.add_item(project_id=1, type_id=24698, quantity=5, me_level=10, te_level=20)

        assert result["type_name"] == "Drake"
        assert result["type_id"] == 24698
        # Verify all 3 queries executed
        assert len(cursor.executed) == 3
        assert "INSERT INTO project_items" in cursor.executed[0][0]
        assert "invTypes" in cursor.executed[1][0]
        assert "UPDATE production_projects" in cursor.executed[2][0]

    def test_adds_item_with_unknown_type(self):
        item_row = _make_item(id=11, type_id=99999)
        del item_row["type_name"]
        cursor = MultiResultCursor([
            [item_row],  # INSERT RETURNING *
            [],           # type name not found
            [],           # UPDATE project updated_at
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.add_item(project_id=1, type_id=99999)

        assert result["type_name"] == "Unknown"


# ==========================================================================
# TestUpdateItem
# ==========================================================================


class TestUpdateItem:
    """Tests for ProjectService.update_item()."""

    def test_updates_quantity_and_me(self):
        updated_item = _make_item(id=10, quantity=20, me_level=5)
        cursor = MultiResultCursor([
            [updated_item],
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.update_item(item_id=10, quantity=20, me_level=5)

        assert result["quantity"] == 20
        assert result["me_level"] == 5
        sql = cursor.executed[0][0]
        assert "UPDATE project_items" in sql
        assert "quantity = %s" in sql
        assert "me_level = %s" in sql

    def test_noop_returns_current_item(self):
        """When no valid kwargs are passed, returns current item."""
        current_item = _make_item(id=10)
        cursor = MultiResultCursor([
            [current_item],
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.update_item(item_id=10, invalid_field="nope")

        assert result is not None
        assert result["id"] == 10
        assert "SELECT * FROM project_items" in cursor.executed[0][0]


# ==========================================================================
# TestDeleteItem
# ==========================================================================


class TestDeleteItem:
    """Tests for ProjectService.delete_item()."""

    def test_returns_true_on_success(self):
        cursor = MultiResultCursor([
            [{"id": 10}],
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.delete_item(item_id=10)

        assert result is True
        assert "DELETE FROM project_items" in cursor.executed[0][0]

    def test_returns_false_when_not_found(self):
        cursor = MultiResultCursor([
            [],
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.delete_item(item_id=999)

        assert result is False


# ==========================================================================
# TestGetDecisions
# ==========================================================================


class TestGetDecisions:
    """Tests for ProjectService.get_decisions()."""

    def test_returns_decisions_with_type_names(self):
        decisions = [
            _make_decision(id=1, material_type_id=34, type_name="Tritanium"),
            _make_decision(id=2, material_type_id=35, type_name="Pyerite", decision="build"),
        ]
        cursor = MultiResultCursor([decisions])
        svc = ProjectService(MockDB(cursor))

        result = svc.get_decisions(item_id=1)

        assert len(result) == 2
        assert result[0]["type_name"] == "Tritanium"
        assert result[1]["decision"] == "build"
        assert cursor.executed[0][1] == (1,)

    def test_returns_empty_list(self):
        cursor = MultiResultCursor([[]])
        svc = ProjectService(MockDB(cursor))

        result = svc.get_decisions(item_id=999)

        assert result == []


# ==========================================================================
# TestSaveDecisions
# ==========================================================================


class TestSaveDecisions:
    """Tests for ProjectService.save_decisions()."""

    def test_saves_batch_of_decisions(self):
        saved = [
            _make_decision(id=10, material_type_id=34, quantity=500),
            _make_decision(id=11, material_type_id=35, quantity=200),
        ]
        # save_decisions calls: execute(DELETE), execute(INSERT), fetchall()
        # Only 1 fetchall, so only 1 result set needed.
        cursor = MultiResultCursor([
            saved,  # consumed by the single fetchall() after INSERT
        ])
        svc = ProjectService(MockDB(cursor))

        decisions_input = [
            {"material_type_id": 34, "decision": "buy", "quantity": 500},
            {"material_type_id": 35, "decision": "buy", "quantity": 200},
        ]
        result = svc.save_decisions(item_id=1, decisions=decisions_input)

        assert len(result) == 2
        # Verify DELETE was called first
        assert "DELETE FROM project_material_decisions" in cursor.executed[0][0]
        assert cursor.executed[0][1] == (1,)
        # Verify INSERT was called second
        assert "INSERT INTO project_material_decisions" in cursor.executed[1][0]

    def test_empty_decisions_just_deletes(self):
        cursor = MultiResultCursor([
            [],  # DELETE existing
        ])
        svc = ProjectService(MockDB(cursor))

        result = svc.save_decisions(item_id=1, decisions=[])

        assert result == []
        # Only DELETE, no INSERT
        assert len(cursor.executed) == 1
        assert "DELETE" in cursor.executed[0][0]

    def test_verify_correct_sql_params(self):
        saved = [
            _make_decision(id=10, material_type_id=34, decision="buy", quantity=500),
        ]
        # Only 1 fetchall call (after INSERT), so 1 result set needed
        cursor = MultiResultCursor([
            saved,  # INSERT RETURNING *
        ])
        svc = ProjectService(MockDB(cursor))

        decisions_input = [
            {"material_type_id": 34, "decision": "buy", "quantity": 500},
        ]
        svc.save_decisions(item_id=7, decisions=decisions_input)

        # DELETE params
        assert cursor.executed[0][1] == (7,)
        # INSERT params: [item_id, material_type_id, decision, quantity]
        insert_params = cursor.executed[1][1]
        assert insert_params == [7, 34, "buy", 500]


# ==========================================================================
# TestShoppingList
# ==========================================================================


class TestShoppingList:
    """Tests for ProjectService.get_shopping_list()."""

    def test_aggregates_buy_decisions_with_prices(self):
        rows = [
            {
                "material_type_id": 34,
                "type_name": "Tritanium",
                "total_quantity": 10000,
                "unit_price": 5.50,
                "needed_by": ["Drake", "Raven"],
            },
            {
                "material_type_id": 35,
                "type_name": "Pyerite",
                "total_quantity": 5000,
                "unit_price": 12.00,
                "needed_by": ["Drake"],
            },
        ]
        cursor = MultiResultCursor([rows])
        svc = ProjectService(MockDB(cursor))

        result = svc.get_shopping_list(project_id=1)

        assert len(result["items"]) == 2
        # Tritanium: 10000 * 5.50 = 55000
        assert result["items"][0]["type_name"] == "Tritanium"
        assert result["items"][0]["total_quantity"] == 10000
        assert result["items"][0]["unit_price"] == 5.50
        assert result["items"][0]["total_price"] == 55000.00
        assert result["items"][0]["needed_by"] == ["Drake", "Raven"]
        # Pyerite: 5000 * 12.00 = 60000
        assert result["items"][1]["total_price"] == 60000.00
        # Total: 55000 + 60000 = 115000
        assert result["total_cost"] == 115000.00

    def test_empty_shopping_list(self):
        cursor = MultiResultCursor([[]])
        svc = ProjectService(MockDB(cursor))

        result = svc.get_shopping_list(project_id=1)

        assert result["items"] == []
        assert result["total_cost"] == 0.0

    def test_handles_zero_price_materials(self):
        rows = [
            {
                "material_type_id": 34,
                "type_name": "Tritanium",
                "total_quantity": 1000,
                "unit_price": 0,
                "needed_by": ["Drake"],
            },
        ]
        cursor = MultiResultCursor([rows])
        svc = ProjectService(MockDB(cursor))

        result = svc.get_shopping_list(project_id=1)

        assert result["items"][0]["total_price"] == 0.0
        assert result["total_cost"] == 0.0

    def test_total_cost_rounding(self):
        """Verify total_cost is rounded to 2 decimal places."""
        rows = [
            {
                "material_type_id": 34,
                "type_name": "Tritanium",
                "total_quantity": 3,
                "unit_price": 1.111,
                "needed_by": ["Drake"],
            },
            {
                "material_type_id": 35,
                "type_name": "Pyerite",
                "total_quantity": 3,
                "unit_price": 2.222,
                "needed_by": ["Drake"],
            },
        ]
        cursor = MultiResultCursor([rows])
        svc = ProjectService(MockDB(cursor))

        result = svc.get_shopping_list(project_id=1)

        # 3 * 1.111 = 3.333, 3 * 2.222 = 6.666 => total = 9.999 => rounded 10.0
        assert result["items"][0]["total_price"] == 3.33
        assert result["items"][1]["total_price"] == 6.67
        assert result["total_cost"] == 10.0
