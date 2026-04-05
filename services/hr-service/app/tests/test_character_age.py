"""Tests for character age calculation logic.

Tests the _calculate_char_age formula from vetting_engine.py,
handling various date formats (ISO string, datetime objects) and
edge cases.
"""

from datetime import datetime, timedelta, timezone

import pytest


# ---- Pure function extracted from VettingEngine._calculate_char_age ----


def calculate_char_age(char_info: dict) -> int | None:
    """Calculate character age in days.

    Reimplemented from VettingEngine._calculate_char_age.
    """
    birthday = char_info.get("birthday")
    if not birthday:
        return None
    try:
        if isinstance(birthday, str):
            bd = datetime.fromisoformat(birthday.replace("Z", "+00:00"))
        else:
            bd = birthday
        return (datetime.utcnow() - bd.replace(tzinfo=None)).days
    except Exception:
        return None


# ---- Tests ----


class TestCharacterAge:
    """Tests for character age calculation."""

    def test_recent_character(self):
        """A character created 30 days ago should return ~30."""
        birthday = (datetime.utcnow() - timedelta(days=30)).isoformat()
        age = calculate_char_age({"birthday": birthday})
        assert age is not None
        assert 29 <= age <= 31

    def test_old_character(self):
        """A character from 2003 should be very old."""
        age = calculate_char_age({"birthday": "2003-06-15T00:00:00Z"})
        assert age is not None
        assert age > 7000  # More than ~19 years

    def test_missing_birthday(self):
        """Missing birthday key should return None."""
        assert calculate_char_age({}) is None

    def test_none_birthday(self):
        """None birthday should return None."""
        assert calculate_char_age({"birthday": None}) is None

    def test_iso_format_with_z(self):
        """ISO format with Z suffix should be parsed correctly."""
        birthday = "2020-01-15T12:00:00Z"
        age = calculate_char_age({"birthday": birthday})
        assert age is not None
        assert age > 1000

    def test_iso_format_with_offset(self):
        """ISO format with timezone offset should be parsed."""
        birthday = "2020-06-01T00:00:00+00:00"
        age = calculate_char_age({"birthday": birthday})
        assert age is not None
        assert age > 1000

    def test_datetime_object_input(self):
        """Datetime objects should also work as input."""
        bd = datetime(2022, 1, 1, tzinfo=timezone.utc)
        age = calculate_char_age({"birthday": bd})
        assert age is not None
        assert age > 500

    def test_young_character_under_90_days(self):
        """Characters under 90 days should be flagged as young in vetting."""
        birthday = (datetime.utcnow() - timedelta(days=45)).isoformat()
        age = calculate_char_age({"birthday": birthday})
        assert age is not None
        assert age < 90

    def test_character_exactly_90_days(self):
        """Character exactly 90 days old should NOT be flagged (boundary)."""
        birthday = (datetime.utcnow() - timedelta(days=90)).isoformat()
        age = calculate_char_age({"birthday": birthday})
        assert age is not None
        # In vetting: age_days < 90, so 90 is NOT flagged
        assert age >= 90

    def test_invalid_date_string(self):
        """Invalid date string should return None, not raise."""
        assert calculate_char_age({"birthday": "not-a-date"}) is None

    def test_empty_string_birthday(self):
        """Empty string birthday should return None."""
        assert calculate_char_age({"birthday": ""}) is None

    def test_character_created_today(self):
        """A character created today should be 0 days old."""
        birthday = datetime.utcnow().isoformat()
        age = calculate_char_age({"birthday": birthday})
        assert age is not None
        assert age == 0
