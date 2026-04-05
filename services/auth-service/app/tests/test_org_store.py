"""Tests for OrgRepository — pure function tests."""
import pytest
from app.repository.org_store import DEFAULT_PERMISSIONS, ALL_PERMISSIONS, VALID_ROLES


class TestDefaultPermissions:
    def test_admin_has_all_permissions(self):
        admin_perms = {p for p, roles in DEFAULT_PERMISSIONS.items() if "admin" in roles}
        assert "members.view" in admin_perms
        assert "members.manage" in admin_perms
        assert "roles.manage" in admin_perms
        assert "audit.view" in admin_perms
        assert "settings.manage" in admin_perms

    def test_officer_has_view_permissions(self):
        officer_perms = {p for p, roles in DEFAULT_PERMISSIONS.items() if "officer" in roles}
        assert "members.view" in officer_perms
        assert "finance.view" in officer_perms
        assert "audit.view" in officer_perms
        assert "members.manage" not in officer_perms
        assert "roles.manage" not in officer_perms

    def test_member_has_fleet_view_only(self):
        member_perms = {p for p, roles in DEFAULT_PERMISSIONS.items() if "member" in roles}
        assert member_perms == {"fleet.view"}

    def test_fleet_commander_permissions(self):
        fc_perms = {p for p, roles in DEFAULT_PERMISSIONS.items() if "fleet_commander" in roles}
        assert "fleet.create" in fc_perms
        assert "fleet.manage" in fc_perms
        assert "fleet.view" in fc_perms
        assert "ops.create" in fc_perms
        assert "ops.manage" in fc_perms

    def test_all_permissions_list_matches(self):
        assert set(ALL_PERMISSIONS) == set(DEFAULT_PERMISSIONS.keys())

    def test_valid_roles(self):
        assert VALID_ROLES == ["admin", "officer", "fleet_commander", "member"]
