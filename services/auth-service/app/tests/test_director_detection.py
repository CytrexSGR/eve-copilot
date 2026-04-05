"""Tests for ESI director detection — pure functions only."""
import pytest
from app.services.director_detection import (
    is_director,
    is_ceo,
    get_highest_corp_role,
    build_role_assignment,
)


class TestIsDirector:
    def test_director_in_roles(self):
        assert is_director(["Director", "Station_Manager"]) is True

    def test_no_director(self):
        assert is_director(["Station_Manager", "Hangar_Take_1"]) is False

    def test_empty_roles(self):
        assert is_director([]) is False

    def test_none_roles(self):
        assert is_director(None) is False

    def test_case_sensitive(self):
        assert is_director(["director"]) is False


class TestIsCeo:
    def test_ceo_in_roles(self):
        assert is_ceo(["CEO"]) is True

    def test_not_ceo(self):
        assert is_ceo(["Director"]) is False


class TestGetHighestCorpRole:
    def test_ceo_wins(self):
        assert get_highest_corp_role(["CEO", "Director"]) == "admin"

    def test_director_is_admin(self):
        assert get_highest_corp_role(["Director", "Station_Manager"]) == "admin"

    def test_station_manager_is_officer(self):
        assert get_highest_corp_role(["Station_Manager"]) == "officer"

    def test_accountant_is_officer(self):
        assert get_highest_corp_role(["Accountant"]) == "officer"

    def test_hangar_access_is_member(self):
        assert get_highest_corp_role(["Hangar_Take_1"]) == "member"

    def test_no_roles_is_none(self):
        assert get_highest_corp_role([]) is None

    def test_none_roles_is_none(self):
        assert get_highest_corp_role(None) is None


class TestBuildRoleAssignment:
    def test_director_assignment(self):
        result = build_role_assignment(
            character_id=12345,
            corporation_id=98378388,
            esi_roles=["Director"],
        )
        assert result["role"] == "admin"
        assert result["character_id"] == 12345
        assert result["corporation_id"] == 98378388
        assert result["auto_assigned"] is True

    def test_no_role_returns_none(self):
        result = build_role_assignment(
            character_id=12345,
            corporation_id=98378388,
            esi_roles=["Hangar_Query_1"],
        )
        assert result is None

    def test_no_corp_returns_none(self):
        result = build_role_assignment(
            character_id=12345,
            corporation_id=None,
            esi_roles=["Director"],
        )
        assert result is None
