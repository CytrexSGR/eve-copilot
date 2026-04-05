"""Tests for doctrine clone, auto-pricing, changelog, and category schemas."""

import os

# Set required env vars BEFORE any app imports
os.environ.setdefault("EVE_CLIENT_ID", "test_client_id")
os.environ.setdefault("EVE_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("EVE_CALLBACK_URL", "http://localhost/callback")

from app.models.schemas import (
    DoctrineCloneRequest,
    DoctrineChangelogEntry,
    DoctrineAutoPriceResponse,
    DoctrineCreate,
    DoctrineResponse,
)


# ──────────────────────── Clone Request Schema ──────────────────────────


def test_clone_request_schema():
    req = DoctrineCloneRequest(new_name="Muninn Fleet v2", category="fleet")
    assert req.new_name == "Muninn Fleet v2"
    assert req.category == "fleet"


def test_clone_request_defaults():
    req = DoctrineCloneRequest(new_name="Copy")
    assert req.category is None


# ──────────────────────── Auto-Price Response ───────────────────────────


def test_auto_price_response_schema():
    resp = DoctrineAutoPriceResponse(
        doctrine_id=1,
        total_price=250000000.0,
        item_prices={
            "11379": {
                "name": "Muninn",
                "quantity": 1,
                "unit_price": 250000000.0,
                "total": 250000000.0,
            }
        },
        price_source="fuzzwork_jita",
        priced_at="2026-02-22T12:00:00Z",
    )
    assert resp.total_price == 250000000.0
    assert resp.price_source == "fuzzwork_jita"
    assert "11379" in resp.item_prices


# ──────────────────────── Changelog Entry ───────────────────────────────


def test_changelog_entry_fields():
    entry = DoctrineChangelogEntry(
        id=1,
        doctrine_id=10,
        actor_character_id=123,
        actor_name="Test Pilot",
        action="created",
        changes={},
        created_at="2026-02-22T12:00:00Z",
    )
    assert entry.action == "created"
    assert entry.actor_name == "Test Pilot"
    assert entry.doctrine_id == 10


def test_changelog_entry_with_changes():
    entry = DoctrineChangelogEntry(
        id=2,
        doctrine_id=10,
        actor_character_id=456,
        actor_name="FC Leader",
        action="updated",
        changes={"name": "New Name", "category": "fleet"},
        created_at="2026-02-22T13:00:00Z",
    )
    assert entry.changes["name"] == "New Name"
    assert entry.changes["category"] == "fleet"


# ──────────────────────── Category in DoctrineCreate ────────────────────


def test_doctrine_create_has_category():
    req = DoctrineCreate(
        corporation_id=98000001,
        name="Test Doctrine",
        ship_type_id=11379,
        fitting={"high": [], "med": [], "low": [], "rig": [], "drones": []},
    )
    assert req.category == "general"


def test_doctrine_create_custom_category():
    req = DoctrineCreate(
        corporation_id=98000001,
        name="Test Doctrine",
        ship_type_id=11379,
        fitting={"high": [], "med": [], "low": [], "rig": [], "drones": []},
        category="pvp",
    )
    assert req.category == "pvp"


# ──────────────────────── Category in DoctrineResponse ──────────────────


def test_doctrine_response_has_category():
    resp = DoctrineResponse(
        id=1,
        corporation_id=98000001,
        name="Test Doctrine",
        ship_type_id=11379,
        fitting_json={"high": [], "med": [], "low": [], "rig": [], "drones": []},
    )
    assert resp.category == "general"


def test_doctrine_response_custom_category():
    resp = DoctrineResponse(
        id=1,
        corporation_id=98000001,
        name="Test Doctrine",
        ship_type_id=11379,
        fitting_json={"high": [], "med": [], "low": [], "rig": [], "drones": []},
        category="mining",
    )
    assert resp.category == "mining"
