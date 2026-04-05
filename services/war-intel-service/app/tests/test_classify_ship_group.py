"""Tests for classify_ship_group() — pure function, no DB required."""

import pytest
from app.routers.intelligence.corp_sql_helpers import classify_ship_group


class TestFrigates:
    @pytest.mark.parametrize("group_name", [
        "Frigate", "Assault Frigate", "Interceptor", "Covert Ops",
        "Electronic Attack Ship", "Stealth Bomber", "Expedition Frigate",
        "Logistics Frigate", "Prototype Exploration Ship",
    ])
    def test_frigate_classes(self, group_name):
        assert classify_ship_group(group_name) == "Frigate"


class TestDestroyers:
    @pytest.mark.parametrize("group_name", [
        "Destroyer", "Interdictor", "Tactical Destroyer", "Command Destroyer",
    ])
    def test_destroyer_classes(self, group_name):
        assert classify_ship_group(group_name) == "Destroyer"


class TestCruisers:
    @pytest.mark.parametrize("group_name", [
        "Cruiser", "Heavy Assault Cruiser", "Strategic Cruiser", "Recon Ship",
        "Heavy Interdiction Cruiser", "Logistics Cruiser", "Logistics",
        "Combat Recon Ship", "Force Recon Ship", "Flag Cruiser",
        "Expedition Command Ship",
    ])
    def test_cruiser_classes(self, group_name):
        assert classify_ship_group(group_name) == "Cruiser"


class TestBattlecruisers:
    @pytest.mark.parametrize("group_name", [
        "Battlecruiser", "Command Ship", "Attack Battlecruiser", "Combat Battlecruiser",
    ])
    def test_battlecruiser_classes(self, group_name):
        assert classify_ship_group(group_name) == "Battlecruiser"


class TestBattleships:
    @pytest.mark.parametrize("group_name", [
        "Battleship", "Black Ops", "Marauder", "Elite Battleship",
    ])
    def test_battleship_classes(self, group_name):
        assert classify_ship_group(group_name) == "Battleship"


class TestCapitals:
    @pytest.mark.parametrize("group_name", [
        "Carrier", "Dreadnought", "\u2666 Dreadnought", "Lancer Dreadnought",
        "Force Auxiliary", "Supercarrier", "Titan",
        "Capital Industrial Ship", "Jump Freighter",
    ])
    def test_capital_classes(self, group_name):
        assert classify_ship_group(group_name) == "Capital"


class TestCapsules:
    @pytest.mark.parametrize("group_name", [
        "Capsule", "Rookie ship", "Shuttle", "Corvette",
    ])
    def test_capsule_classes(self, group_name):
        assert classify_ship_group(group_name) == "Capsule"


class TestStructures:
    @pytest.mark.parametrize("group_name", [
        "Citadel", "Engineering Complex", "\u2666 Engineering Complex", "Refinery",
        "Administration Hub", "Observatory", "Stargate", "Upwell Jump Gate",
        "Control Tower", "Infrastructure Upgrades",
    ])
    def test_structure_classes(self, group_name):
        assert classify_ship_group(group_name) == "Structure"


class TestIndustrials:
    @pytest.mark.parametrize("group_name", [
        "Mining Barge", "Exhumer", "Industrial", "Transport Ship",
        "Deep Space Transport", "Blockade Runner", "Freighter",
        "Industrial Command Ship",
    ])
    def test_industrial_classes(self, group_name):
        assert classify_ship_group(group_name) == "Industrial"


class TestFightersDrones:
    @pytest.mark.parametrize("group_name", [
        "Fighter", "Fighter-Bomber", "Light Fighter", "Heavy Fighter",
        "Structure Fighter", "Structure Heavy Fighter", "Structure Light Fighter",
        "Combat Drone", "Logistic Drone", "Mining Drone", "Electronic Warfare Drone",
    ])
    def test_fighter_drone_classes(self, group_name):
        assert classify_ship_group(group_name) == "Fighter/Drone"


class TestDeployables:
    @pytest.mark.parametrize("group_name", [
        "Mobile Warp Disruptor", "Mobile Cyno Inhibitor", "Mobile Depot",
        "Mobile Siphon Unit", "Mobile Scan Inhibitor", "Mobile Micro Jump Unit",
        "Mercenary Den", "Upwell Moon Drill", "Upwell Cyno Jammer",
        "Upwell Cyno Beacon", "Deployable", "Mobile Tractor Unit", "Skyhook",
        "Mobile Phase Anchor",
    ])
    def test_deployable_classes(self, group_name):
        assert classify_ship_group(group_name) == "Deployable"


class TestOther:
    @pytest.mark.parametrize("group_name", [
        "Unknown Ship", "Warp Gate", "Customs Office", "",
    ])
    def test_unknown_returns_other(self, group_name):
        assert classify_ship_group(group_name) == "Other"


class TestAllCategories:
    def test_all_twelve_categories_covered(self):
        """Verify that all 12 expected categories are reachable."""
        expected = {
            "Frigate", "Destroyer", "Cruiser", "Battlecruiser", "Battleship",
            "Capital", "Capsule", "Structure", "Industrial", "Fighter/Drone",
            "Deployable", "Other",
        }
        results = set()
        test_inputs = [
            "Frigate", "Destroyer", "Cruiser", "Battlecruiser", "Battleship",
            "Carrier", "Capsule", "Citadel", "Mining Barge", "Fighter",
            "Mobile Depot", "Unknown Ship",
        ]
        for name in test_inputs:
            results.add(classify_ship_group(name))
        assert results == expected
