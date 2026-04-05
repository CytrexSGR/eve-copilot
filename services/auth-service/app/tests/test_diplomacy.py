"""Tests for diplomacy router schemas and logic."""
import pytest
from pydantic import ValidationError


def test_alumni_note_schema():
    """Test AlumniNote Pydantic model."""
    from app.routers.diplomacy import AlumniNote
    note = AlumniNote(
        character_id=12345,
        character_name="Test Pilot",
        note="Left for greener pastures",
    )
    assert note.character_id == 12345
    assert note.note == "Left for greener pastures"


def test_alumni_note_schema_empty_note():
    """Test AlumniNote with empty note is valid."""
    from app.routers.diplomacy import AlumniNote
    note = AlumniNote(character_id=12345, character_name="Test Pilot")
    assert note.note == ""


def test_alumni_note_requires_character_id():
    """Test that character_id is required."""
    from app.routers.diplomacy import AlumniNote
    with pytest.raises(ValidationError):
        AlumniNote(character_name="Test Pilot")


def test_alumni_response_schema():
    """Test AlumniMember response model."""
    from app.routers.diplomacy import AlumniMember
    member = AlumniMember(
        character_id=12345,
        character_name="Test Pilot",
        left_at="2026-01-15T12:00:00Z",
        destination_corp_id=98000001,
        destination_corp_name="New Corp",
        note="Friendly departure",
        noted_by_name="FC Leader",
    )
    assert member.destination_corp_name == "New Corp"


def test_standings_entry_schema():
    """Test StandingEntry response model."""
    from app.routers.diplomacy import StandingEntry
    entry = StandingEntry(
        contact_id=98000001,
        contact_name="Allied Corp",
        contact_type="corporation",
        standing=10.0,
        is_watched=True,
    )
    assert entry.standing == 10.0
    assert entry.contact_type == "corporation"
