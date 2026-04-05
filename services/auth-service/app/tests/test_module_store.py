"""Tests for module subscription repository — pure function tests, no DB."""
import pytest
from datetime import datetime, timezone, timedelta

from app.repository.module_store import (
    resolve_active_modules,
    build_module_jwt_claims,
    is_trial_available,
    expand_bundle,
    has_module_access,
    BUNDLE_CONTENTS,
    ENTITY_MODULE_GROUPS,
)


class MockCursor:
    """Mock cursor for DB function tests."""

    def __init__(self, results=None):
        self._results = results or []

    def execute(self, query, params=None):
        pass

    def fetchall(self):
        return self._results

    def fetchone(self):
        return self._results[0] if self._results else None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# --- resolve_active_modules ---

class TestResolveActiveModules:

    def test_empty_subscriptions(self):
        result = resolve_active_modules([])
        assert result == []

    def test_single_active_module(self):
        future = datetime.now(timezone.utc) + timedelta(days=10)
        rows = [{"module_name": "warfare_intel", "expires_at": future, "scope": {}}]
        result = resolve_active_modules(rows)
        assert result == ["warfare_intel"]

    def test_expired_module_excluded(self):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        rows = [{"module_name": "warfare_intel", "expires_at": past, "scope": {}}]
        result = resolve_active_modules(rows)
        assert result == []

    def test_multiple_active_modules_sorted(self):
        future = datetime.now(timezone.utc) + timedelta(days=10)
        rows = [
            {"module_name": "warfare_intel", "expires_at": future, "scope": {}},
            {"module_name": "character_suite", "expires_at": future, "scope": {}},
        ]
        result = resolve_active_modules(rows)
        assert result == ["character_suite", "warfare_intel"]

    def test_deduplicates_same_module(self):
        future = datetime.now(timezone.utc) + timedelta(days=10)
        rows = [
            {"module_name": "warfare_intel", "expires_at": future, "scope": {}},
            {"module_name": "warfare_intel", "expires_at": future + timedelta(days=5), "scope": {}},
        ]
        result = resolve_active_modules(rows)
        assert result == ["warfare_intel"]

    def test_mix_of_active_and_expired(self):
        future = datetime.now(timezone.utc) + timedelta(days=10)
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        rows = [
            {"module_name": "warfare_intel", "expires_at": future, "scope": {}},
            {"module_name": "war_economy", "expires_at": past, "scope": {}},
            {"module_name": "character_suite", "expires_at": future, "scope": {}},
        ]
        result = resolve_active_modules(rows)
        assert result == ["character_suite", "warfare_intel"]
        assert "war_economy" not in result


# --- build_module_jwt_claims ---

class TestBuildModuleJwtClaims:

    def test_empty_modules_no_org(self):
        claims = build_module_jwt_claims([], None)
        assert claims == {"active_modules": [], "org_plan": None}

    def test_with_modules_no_org(self):
        claims = build_module_jwt_claims(["warfare_intel", "wormhole_intel"], None)
        assert claims["active_modules"] == ["warfare_intel", "wormhole_intel"]
        assert claims["org_plan"] is None

    def test_with_modules_and_org_plan(self):
        org = {"type": "corporation", "plan": "standard", "has_seat": True}
        claims = build_module_jwt_claims(["warfare_intel"], org)
        assert claims["active_modules"] == ["warfare_intel"]
        assert claims["org_plan"] == org

    def test_empty_modules_with_org_plan(self):
        org = {"type": "alliance", "plan": "premium", "has_seat": False}
        claims = build_module_jwt_claims([], org)
        assert claims["active_modules"] == []
        assert claims["org_plan"] == org


# --- is_trial_available ---

class TestIsTrialAvailable:

    def test_no_history_means_available(self):
        assert is_trial_available([], "warfare_intel") is True

    def test_already_used_not_available(self):
        rows = [{"module_name": "warfare_intel", "trial_used": True}]
        assert is_trial_available(rows, "warfare_intel") is False

    def test_different_module_trial_still_available(self):
        rows = [{"module_name": "war_economy", "trial_used": True}]
        assert is_trial_available(rows, "warfare_intel") is True

    def test_same_module_but_not_trial(self):
        """A paid subscription (trial_used=False) does not block trial."""
        rows = [{"module_name": "warfare_intel", "trial_used": False}]
        assert is_trial_available(rows, "warfare_intel") is True

    def test_multiple_modules_one_used(self):
        rows = [
            {"module_name": "warfare_intel", "trial_used": True},
            {"module_name": "war_economy", "trial_used": False},
        ]
        assert is_trial_available(rows, "warfare_intel") is False
        assert is_trial_available(rows, "war_economy") is True
        assert is_trial_available(rows, "character_suite") is True


# --- expand_bundle ---

class TestExpandBundle:

    def test_intel_pack_has_5_modules(self):
        modules = expand_bundle("intel_pack")
        assert len(modules) == 5
        assert "warfare_intel" in modules
        assert "war_economy" in modules
        assert "wormhole_intel" in modules
        assert "doctrine_intel" in modules
        assert "battle_analysis" in modules

    def test_entity_pack_has_3_modules(self):
        modules = expand_bundle("entity_pack")
        assert len(modules) == 3
        assert "corp_intel_unlimited" in modules
        assert "alliance_intel_unlimited" in modules
        assert "powerbloc_intel_unlimited" in modules

    def test_pilot_complete_has_10_modules(self):
        modules = expand_bundle("pilot_complete")
        assert len(modules) == 10
        # All intel modules
        for mod in BUNDLE_CONTENTS["intel_pack"]:
            assert mod in modules
        # Personal modules
        assert "character_suite" in modules
        assert "market_analysis" in modules
        # Entity unlimited
        for mod in BUNDLE_CONTENTS["entity_pack"]:
            assert mod in modules

    def test_non_bundle_returns_single(self):
        modules = expand_bundle("warfare_intel")
        assert modules == ["warfare_intel"]

    def test_unknown_name_returns_single(self):
        modules = expand_bundle("nonexistent_module")
        assert modules == ["nonexistent_module"]


# --- has_module_access ---

class TestHasModuleAccess:

    def test_exact_match(self):
        assert has_module_access(["warfare_intel"], "warfare_intel") is True

    def test_no_match(self):
        assert has_module_access(["warfare_intel"], "war_economy") is False

    def test_empty_modules(self):
        assert has_module_access([], "warfare_intel") is False

    def test_entity_group_corp_intel_5_grants_corp_intel(self):
        """corp_intel_5 subscription grants access to corp_intel."""
        assert has_module_access(["corp_intel_5"], "corp_intel") is True

    def test_entity_group_corp_intel_1_grants_corp_intel(self):
        assert has_module_access(["corp_intel_1"], "corp_intel") is True

    def test_entity_group_corp_intel_unlimited_grants_corp_intel(self):
        assert has_module_access(["corp_intel_unlimited"], "corp_intel") is True

    def test_entity_group_alliance_intel_5_grants_alliance_intel(self):
        assert has_module_access(["alliance_intel_5"], "alliance_intel") is True

    def test_entity_group_powerbloc_intel_1_grants_powerbloc_intel(self):
        assert has_module_access(["powerbloc_intel_1"], "powerbloc_intel") is True

    def test_entity_group_does_not_cross_types(self):
        """corp_intel_5 does NOT grant alliance_intel."""
        assert has_module_access(["corp_intel_5"], "alliance_intel") is False

    def test_multiple_modules_one_matches(self):
        modules = ["warfare_intel", "corp_intel_5", "character_suite"]
        assert has_module_access(modules, "corp_intel") is True
        assert has_module_access(modules, "warfare_intel") is True
        assert has_module_access(modules, "character_suite") is True
        assert has_module_access(modules, "alliance_intel") is False


# --- BUNDLE_CONTENTS integrity ---

class TestBundleContentsIntegrity:

    def test_pilot_complete_is_superset_of_intel_and_entity(self):
        """pilot_complete must contain all intel_pack + entity_pack modules."""
        pilot = set(BUNDLE_CONTENTS["pilot_complete"])
        intel = set(BUNDLE_CONTENTS["intel_pack"])
        entity = set(BUNDLE_CONTENTS["entity_pack"])
        assert intel.issubset(pilot)
        assert entity.issubset(pilot)

    def test_no_duplicate_modules_in_bundles(self):
        for bundle_name, modules in BUNDLE_CONTENTS.items():
            assert len(modules) == len(set(modules)), (
                f"Duplicate modules in {bundle_name}"
            )
