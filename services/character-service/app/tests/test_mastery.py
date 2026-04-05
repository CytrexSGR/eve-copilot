"""Tests for mastery_service.py — _calculate_mastery_level pure function."""

import pytest

from app.services.mastery_service import _calculate_mastery_level


# ---------------------------------------------------------------------------
# Helpers: build mastery requirements
# ---------------------------------------------------------------------------

def _make_mastery_reqs(levels_certs):
    """Build mastery_reqs dict from compact spec.

    levels_certs: dict of level -> list of (cert_name, [(skill_id, skill_name, level)])
    """
    reqs = {}
    for lvl, certs in levels_certs.items():
        reqs[lvl] = []
        for cert_name, skills in certs:
            reqs[lvl].append({
                "cert_id": hash(cert_name) % 10000,
                "cert_name": cert_name,
                "skills": [
                    {"skill_id": sid, "skill_name": sname, "level": slvl}
                    for sid, sname, slvl in skills
                ],
            })
    return reqs


# ---------------------------------------------------------------------------
# Tests: achieved mastery level
# ---------------------------------------------------------------------------

class TestMasteryLevelCalculation:
    """Test _calculate_mastery_level with various skill/requirement combos."""

    def test_no_skills_returns_negative_one(self):
        """No skills at all -> mastery -1 (None)."""
        reqs = _make_mastery_reqs({
            0: [("Shield", [(3416, "Shield Operation", 1)])],
        })
        result = _calculate_mastery_level({}, reqs)
        assert result["mastery_level"] == -1

    def test_all_level_zero_met(self):
        """All level-0 cert skills met -> mastery 0."""
        reqs = _make_mastery_reqs({
            0: [("Shield", [(3416, "Shield Operation", 1)])],
            1: [("Shield", [(3416, "Shield Operation", 3)])],
        })
        char_skills = {3416: 1}
        result = _calculate_mastery_level(char_skills, reqs)
        assert result["mastery_level"] == 0

    def test_all_levels_met(self):
        """Character has all skills at level 5 -> mastery 4 (Elite)."""
        reqs = _make_mastery_reqs({
            0: [("Shield", [(3416, "Shield Operation", 1)])],
            1: [("Shield", [(3416, "Shield Operation", 2)])],
            2: [("Shield", [(3416, "Shield Operation", 3)])],
            3: [("Shield", [(3416, "Shield Operation", 4)])],
            4: [("Shield", [(3416, "Shield Operation", 5)])],
        })
        char_skills = {3416: 5}
        result = _calculate_mastery_level(char_skills, reqs)
        assert result["mastery_level"] == 4

    def test_partial_mastery(self):
        """Character meets levels 0-2 but not 3 -> mastery 2."""
        reqs = _make_mastery_reqs({
            0: [("Nav", [(3449, "Navigation", 1)])],
            1: [("Nav", [(3449, "Navigation", 2)])],
            2: [("Nav", [(3449, "Navigation", 3)])],
            3: [("Nav", [(3449, "Navigation", 4), (3453, "Warp Drive Op", 4)])],
        })
        char_skills = {3449: 3, 3453: 2}
        result = _calculate_mastery_level(char_skills, reqs)
        assert result["mastery_level"] == 2

    def test_highest_consecutive_level_tracked(self):
        """Mastery tracks the highest met level; the function records last met."""
        reqs = _make_mastery_reqs({
            0: [("A", [(100, "Alpha", 1)])],
            1: [("A", [(100, "Alpha", 3)])],  # not met (need 3, have 2)
            2: [("A", [(100, "Alpha", 2)])],  # met (need 2, have 2)
        })
        char_skills = {100: 2}
        result = _calculate_mastery_level(char_skills, reqs)
        # The function iterates 0-4 and sets achieved_level each time a level passes.
        # Level 0: met (need 1, have 2) -> achieved=0
        # Level 1: not met (need 3, have 2) -> achieved stays 0
        # Level 2: met (need 2, have 2) -> achieved=2
        assert result["mastery_level"] == 2

    def test_multiple_certs_per_level(self):
        """All certs in a level must be met for that level to pass."""
        reqs = _make_mastery_reqs({
            0: [
                ("Shield", [(3416, "Shield Operation", 1)]),
                ("Armor", [(3392, "Mechanics", 1)]),
            ],
        })
        # Only Shield met, not Armor
        char_skills = {3416: 1}
        result = _calculate_mastery_level(char_skills, reqs)
        assert result["mastery_level"] == -1

    def test_multiple_certs_all_met(self):
        """All certs in level 0 met -> mastery 0."""
        reqs = _make_mastery_reqs({
            0: [
                ("Shield", [(3416, "Shield Operation", 1)]),
                ("Armor", [(3392, "Mechanics", 1)]),
            ],
        })
        char_skills = {3416: 1, 3392: 1}
        result = _calculate_mastery_level(char_skills, reqs)
        assert result["mastery_level"] == 0


# ---------------------------------------------------------------------------
# Tests: missing skills
# ---------------------------------------------------------------------------

class TestMasteryMissingSkills:
    """Test the missing_for_next output from _calculate_mastery_level."""

    def test_missing_skills_reported(self):
        """Missing skills for the next unachieved level are listed."""
        reqs = _make_mastery_reqs({
            0: [("Nav", [(3449, "Navigation", 3)])],
        })
        char_skills = {3449: 1}
        result = _calculate_mastery_level(char_skills, reqs)
        assert result["mastery_level"] == -1
        missing = result["missing_for_next"]
        assert len(missing) >= 1
        nav_missing = [m for m in missing if m["skill"] == "Navigation"]
        assert nav_missing[0]["have"] == 1
        assert nav_missing[0]["need"] == 3

    def test_missing_skills_deduplication(self):
        """Same skill in multiple certs is deduplicated, highest level kept."""
        reqs = _make_mastery_reqs({
            0: [
                ("CertA", [(3416, "Shield Operation", 3)]),
                ("CertB", [(3416, "Shield Operation", 5)]),
            ],
        })
        char_skills = {3416: 1}
        result = _calculate_mastery_level(char_skills, reqs)
        missing = result["missing_for_next"]
        shield_missing = [m for m in missing if m["skill"] == "Shield Operation"]
        assert len(shield_missing) == 1
        assert shield_missing[0]["need"] == 5  # highest requirement

    def test_missing_skills_limited_to_ten(self):
        """Missing skills list is limited to 10 entries."""
        skills = [(i, f"Skill{i}", 5) for i in range(100, 115)]
        reqs = _make_mastery_reqs({0: [("BigCert", skills)]})
        char_skills = {}
        result = _calculate_mastery_level(char_skills, reqs)
        assert len(result["missing_for_next"]) <= 10

    def test_no_missing_when_all_met(self):
        """When mastery is fully achieved, missing_for_next may be empty."""
        reqs = _make_mastery_reqs({
            0: [("Nav", [(3449, "Navigation", 1)])],
        })
        char_skills = {3449: 5}
        result = _calculate_mastery_level(char_skills, reqs)
        assert result["mastery_level"] == 0
        # No levels above 0 defined, so no missing for "next"


# ---------------------------------------------------------------------------
# Tests: certificate status
# ---------------------------------------------------------------------------

class TestMasteryCertificateStatus:
    """Test the certificates dict from _calculate_mastery_level."""

    def test_cert_status_structure(self):
        """Each level has 'complete' bool and 'certificates' list."""
        reqs = _make_mastery_reqs({
            0: [("Shield", [(3416, "Shield Operation", 1)])],
        })
        result = _calculate_mastery_level({3416: 1}, reqs)
        assert 0 in result["certificates"]
        level_0 = result["certificates"][0]
        assert "complete" in level_0
        assert "certificates" in level_0
        assert level_0["complete"] is True

    def test_incomplete_cert_has_missing_list(self):
        """Incomplete certificate includes missing skill entries."""
        reqs = _make_mastery_reqs({
            0: [("Shield", [(3416, "Shield Operation", 3)])],
        })
        result = _calculate_mastery_level({3416: 1}, reqs)
        level_0 = result["certificates"][0]
        assert level_0["complete"] is False
        cert = level_0["certificates"][0]
        assert cert["complete"] is False
        assert len(cert["missing"]) == 1
        assert cert["missing"][0]["have"] == 1
        assert cert["missing"][0]["need"] == 3

    def test_empty_mastery_reqs(self):
        """Empty mastery requirements -> mastery -1, no certs."""
        result = _calculate_mastery_level({3416: 5}, {})
        assert result["mastery_level"] == -1
        assert result["certificates"] == {}
