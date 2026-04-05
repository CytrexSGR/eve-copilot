"""Tests for Pydantic model validation.

Tests the schema validation rules in models/schemas.py:
- RedListEntity category validation
- Severity bounds (1-5)
- VettingReport risk_score bounds (0-100)
- Required fields
- Default values
"""

from datetime import datetime

import pytest

# Import Pydantic models directly (no DB dependencies)
from app.models.schemas import (
    RedListEntity,
    RedListCreateRequest,
    RedListBulkRequest,
    VettingCheckRequest,
    VettingReport,
    RoleMapping,
    RoleMappingCreate,
    FleetSessionCreate,
    ActivitySummary,
    SkillSnapshot,
)


class TestRedListEntityValidation:
    """Tests for RedListEntity Pydantic model."""

    def test_valid_character_category(self):
        """Category 'character' should be accepted."""
        entity = RedListEntity(entity_id=123, category="character")
        assert entity.category == "character"

    def test_valid_corporation_category(self):
        """Category 'corporation' should be accepted."""
        entity = RedListEntity(entity_id=123, category="corporation")
        assert entity.category == "corporation"

    def test_valid_alliance_category(self):
        """Category 'alliance' should be accepted."""
        entity = RedListEntity(entity_id=123, category="alliance")
        assert entity.category == "alliance"

    def test_invalid_category_rejected(self):
        """Invalid categories should raise validation error."""
        with pytest.raises(Exception):
            RedListEntity(entity_id=123, category="fleet")

    def test_severity_default_is_1(self):
        """Default severity should be 1."""
        entity = RedListEntity(entity_id=123, category="character")
        assert entity.severity == 1

    def test_severity_min_1(self):
        """Severity below 1 should be rejected."""
        with pytest.raises(Exception):
            RedListEntity(entity_id=123, category="character", severity=0)

    def test_severity_max_5(self):
        """Severity above 5 should be rejected."""
        with pytest.raises(Exception):
            RedListEntity(entity_id=123, category="character", severity=6)

    def test_severity_5_accepted(self):
        """Maximum severity 5 should be accepted."""
        entity = RedListEntity(entity_id=123, category="character", severity=5)
        assert entity.severity == 5

    def test_active_default_true(self):
        """Default active status should be True."""
        entity = RedListEntity(entity_id=123, category="character")
        assert entity.active is True

    def test_optional_fields_default_none(self):
        """Optional fields should default to None."""
        entity = RedListEntity(entity_id=123, category="character")
        assert entity.entity_name is None
        assert entity.reason is None
        assert entity.added_by is None
        assert entity.added_at is None
        assert entity.id is None


class TestRedListCreateRequest:
    """Tests for RedListCreateRequest validation."""

    def test_minimal_valid_request(self):
        """Minimum required fields should be accepted."""
        req = RedListCreateRequest(entity_id=12345, category="character")
        assert req.entity_id == 12345

    def test_full_request(self):
        """All fields populated should be accepted."""
        req = RedListCreateRequest(
            entity_id=12345,
            entity_name="Test Pilot",
            category="character",
            severity=3,
            reason="Known spy",
            added_by="HR Officer",
        )
        assert req.entity_name == "Test Pilot"
        assert req.severity == 3


class TestRedListBulkRequest:
    """Tests for RedListBulkRequest validation."""

    def test_single_entity_bulk(self):
        """Bulk request with one entity should be valid."""
        bulk = RedListBulkRequest(
            entities=[RedListCreateRequest(entity_id=1, category="character")]
        )
        assert len(bulk.entities) == 1

    def test_multiple_entities_bulk(self):
        """Bulk request with multiple entities."""
        bulk = RedListBulkRequest(
            entities=[
                RedListCreateRequest(entity_id=1, category="character"),
                RedListCreateRequest(entity_id=2, category="corporation"),
                RedListCreateRequest(entity_id=3, category="alliance"),
            ]
        )
        assert len(bulk.entities) == 3


class TestVettingReport:
    """Tests for VettingReport validation."""

    def test_risk_score_min_0(self):
        """Risk score below 0 should be rejected."""
        with pytest.raises(Exception):
            VettingReport(character_id=123, risk_score=-1)

    def test_risk_score_max_100(self):
        """Risk score above 100 should be rejected."""
        with pytest.raises(Exception):
            VettingReport(character_id=123, risk_score=101)

    def test_risk_score_0_accepted(self):
        """Risk score 0 (clean) should be valid."""
        report = VettingReport(character_id=123, risk_score=0)
        assert report.risk_score == 0

    def test_risk_score_100_accepted(self):
        """Risk score 100 (maximum risk) should be valid."""
        report = VettingReport(character_id=123, risk_score=100)
        assert report.risk_score == 100

    def test_default_empty_collections(self):
        """Default collections should be empty."""
        report = VettingReport(character_id=123)
        assert report.flags == {}
        assert report.red_list_hits == []
        assert report.wallet_flags == []
        assert report.skill_flags == []

    def test_risk_score_default_0(self):
        """Default risk score should be 0."""
        report = VettingReport(character_id=123)
        assert report.risk_score == 0


class TestVettingCheckRequest:
    """Tests for VettingCheckRequest validation."""

    def test_defaults_all_checks_enabled(self):
        """By default, all checks should be enabled."""
        req = VettingCheckRequest(character_id=123)
        assert req.check_contacts is True
        assert req.check_wallet is True
        assert req.check_skills is True

    def test_selective_checks(self):
        """Individual checks can be disabled."""
        req = VettingCheckRequest(
            character_id=123,
            check_contacts=False,
            check_wallet=True,
            check_skills=False,
        )
        assert req.check_contacts is False
        assert req.check_wallet is True
        assert req.check_skills is False


class TestRoleMapping:
    """Tests for RoleMapping validation."""

    def test_valid_mapping(self):
        """Basic role mapping should be accepted."""
        mapping = RoleMapping(esi_role="Director", web_permission="admin")
        assert mapping.priority == 0
        assert mapping.active is True

    def test_custom_priority(self):
        """Custom priority should be stored."""
        mapping = RoleMapping(esi_role="Director", web_permission="admin", priority=10)
        assert mapping.priority == 10


class TestFleetSessionCreate:
    """Tests for FleetSessionCreate validation."""

    def test_minimal_session(self):
        """Minimum required fields for fleet session."""
        session = FleetSessionCreate(
            character_id=123,
            start_time=datetime(2026, 1, 15, 20, 0, 0),
        )
        assert session.character_id == 123
        assert session.fleet_id is None
        assert session.end_time is None


class TestSkillSnapshot:
    """Tests for SkillSnapshot validation."""

    def test_valid_snapshot(self):
        """Valid snapshot should be accepted."""
        snap = SkillSnapshot(character_id=123, total_sp=5000000)
        assert snap.unallocated_sp == 0

    def test_zero_unallocated(self):
        """Zero unallocated SP is the default."""
        snap = SkillSnapshot(character_id=123, total_sp=1000)
        assert snap.unallocated_sp == 0
