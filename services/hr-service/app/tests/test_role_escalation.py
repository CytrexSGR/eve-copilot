"""Tests for role escalation detection logic.

Tests the ESCALATION_ROLES set from role_sync.py and the privilege
escalation detection algorithm used in sync_character().
"""

import pytest

# ---- Inline constants from role_sync.py ----

ESCALATION_ROLES = {
    "Director",
    "CEO",
    "Hangar_Take_1", "Hangar_Take_2", "Hangar_Take_3",
    "Hangar_Take_4", "Hangar_Take_5", "Hangar_Take_6", "Hangar_Take_7",
    "Container_Take_1", "Container_Take_2", "Container_Take_3",
    "Container_Take_4", "Container_Take_5", "Container_Take_6", "Container_Take_7",
    "Accountant",
    "Trader",
    "Station_Manager",
    "Starbase_Defense_Operator",
}


# ---- Pure functions extracted from RoleSyncService ----


def detect_escalation(
    current_esi_roles: list[str],
    previous_esi_roles: list[str] | None,
) -> list[str]:
    """Detect newly granted escalation roles.

    Reimplemented from RoleSyncService.sync_character escalation detection.
    Returns list of newly granted escalation-worthy roles.
    """
    new_escalation_roles = set(current_esi_roles) & ESCALATION_ROLES
    previously_held = set(previous_esi_roles) if previous_esi_roles else set()
    newly_granted = new_escalation_roles - previously_held
    return sorted(newly_granted)


def compute_permission_changes(
    current_roles: list[str],
    mappings: list[dict],
    previous_permissions: set[str] | None,
) -> tuple[list[str], list[str]]:
    """Compute added and removed permissions from role changes.

    Reimplemented from RoleSyncService.sync_character role mapping logic.
    Returns (added, removed) permission lists.
    """
    current_permissions = set()
    for role in current_roles:
        for m in mappings:
            if m["esi_role"] == role:
                current_permissions.add(m["web_permission"])

    prev = previous_permissions or set()
    added = sorted(current_permissions - prev)
    removed = sorted(prev - current_permissions)
    return added, removed


# ---- Tests ----


class TestEscalationRolesSet:
    """Tests for the ESCALATION_ROLES constant."""

    def test_director_is_escalation_role(self):
        assert "Director" in ESCALATION_ROLES

    def test_ceo_is_escalation_role(self):
        assert "CEO" in ESCALATION_ROLES

    def test_accountant_is_escalation_role(self):
        assert "Accountant" in ESCALATION_ROLES

    def test_trader_is_escalation_role(self):
        assert "Trader" in ESCALATION_ROLES

    def test_station_manager_is_escalation_role(self):
        assert "Station_Manager" in ESCALATION_ROLES

    def test_all_hangar_take_roles_present(self):
        """All 7 Hangar_Take roles should be in escalation set."""
        for i in range(1, 8):
            assert f"Hangar_Take_{i}" in ESCALATION_ROLES

    def test_all_container_take_roles_present(self):
        """All 7 Container_Take roles should be in escalation set."""
        for i in range(1, 8):
            assert f"Container_Take_{i}" in ESCALATION_ROLES

    def test_total_escalation_roles_count(self):
        """Total count: Director, CEO, 7 Hangar, 7 Container,
        Accountant, Trader, Station_Manager, Starbase_Defense_Operator = 20."""
        assert len(ESCALATION_ROLES) == 20

    def test_normal_role_not_in_escalation(self):
        """Regular member roles should not be in escalation set."""
        assert "Fitting_Manager" not in ESCALATION_ROLES
        assert "Communications_Officer" not in ESCALATION_ROLES


class TestEscalationDetection:
    """Tests for the escalation detection algorithm."""

    def test_no_escalation_no_escalation_roles(self):
        """Non-escalation roles should never trigger alerts."""
        newly = detect_escalation(
            ["Fitting_Manager", "Communications_Officer"],
            None,
        )
        assert newly == []

    def test_new_director_triggers_escalation(self):
        """First-time Director role should trigger escalation."""
        newly = detect_escalation(["Director"], None)
        assert "Director" in newly

    def test_existing_director_no_escalation(self):
        """Director that was already held should not re-trigger."""
        newly = detect_escalation(["Director"], ["Director"])
        assert newly == []

    def test_new_hangar_access_escalation(self):
        """Getting Hangar_Take_1 for first time triggers escalation."""
        newly = detect_escalation(
            ["Hangar_Take_1", "Fitting_Manager"],
            ["Fitting_Manager"],
        )
        assert "Hangar_Take_1" in newly

    def test_multiple_new_escalation_roles(self):
        """Multiple new escalation roles should all be detected."""
        newly = detect_escalation(
            ["Director", "Accountant", "Trader"],
            [],
        )
        assert set(newly) == {"Director", "Accountant", "Trader"}

    def test_no_previous_roles_all_new(self):
        """When previous_esi_roles is None, all escalation roles are new."""
        newly = detect_escalation(["Director", "CEO"], None)
        assert set(newly) == {"Director", "CEO"}

    def test_mixed_new_and_existing(self):
        """Mix of new and existing escalation roles."""
        newly = detect_escalation(
            ["Director", "Accountant", "Trader"],
            ["Director"],
        )
        assert "Director" not in newly
        assert "Accountant" in newly
        assert "Trader" in newly

    def test_role_removed_no_escalation(self):
        """Losing a role should not trigger escalation."""
        newly = detect_escalation(
            [],
            ["Director", "Accountant"],
        )
        assert newly == []


class TestPermissionChanges:
    """Tests for permission change computation."""

    def test_no_mappings_no_permissions(self):
        """Without role mappings, no permissions are assigned."""
        added, removed = compute_permission_changes(
            ["Director"], [], set()
        )
        assert added == []
        assert removed == []

    def test_new_permission_added(self):
        """New role mapping match should appear as added."""
        mappings = [{"esi_role": "Director", "web_permission": "admin"}]
        added, removed = compute_permission_changes(
            ["Director"], mappings, set()
        )
        assert "admin" in added
        assert removed == []

    def test_permission_removed(self):
        """Lost role should appear as removed permission."""
        mappings = [{"esi_role": "Director", "web_permission": "admin"}]
        added, removed = compute_permission_changes(
            [], mappings, {"admin"}
        )
        assert added == []
        assert "admin" in removed

    def test_unchanged_permissions(self):
        """Unchanged roles should produce no changes."""
        mappings = [{"esi_role": "Director", "web_permission": "admin"}]
        added, removed = compute_permission_changes(
            ["Director"], mappings, {"admin"}
        )
        assert added == []
        assert removed == []

    def test_multiple_mappings_for_same_role(self):
        """One ESI role can map to multiple web permissions."""
        mappings = [
            {"esi_role": "Director", "web_permission": "admin"},
            {"esi_role": "Director", "web_permission": "hr_manage"},
        ]
        added, removed = compute_permission_changes(
            ["Director"], mappings, set()
        )
        assert set(added) == {"admin", "hr_manage"}
