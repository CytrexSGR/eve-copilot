"""Tests for opportunity_scorer.py pure functions and constants."""

import pytest

from app.services.opportunity_scorer import (
    EFFECT_INFO,
    STRUCTURE_GROUPS,
    SHIP_CLASSES,
    THREAT_SHIPS,
    OpportunityScorer,
)


# ---------------------------------------------------------------------------
# Constants integrity
# ---------------------------------------------------------------------------

class TestEffectInfo:
    """Validate EFFECT_INFO constant structure."""

    def test_all_six_effects_present(self):
        expected = {'Wolf-Rayet', 'Pulsar', 'Magnetar', 'Black Hole',
                    'Cataclysmic Variable', 'Red Giant'}
        assert set(EFFECT_INFO.keys()) == expected

    @pytest.mark.parametrize("effect", list(EFFECT_INFO.keys()))
    def test_effect_has_required_keys(self, effect):
        info = EFFECT_INFO[effect]
        assert 'icon' in info
        assert 'bonus' in info
        assert 'color' in info

    @pytest.mark.parametrize("effect", list(EFFECT_INFO.keys()))
    def test_effect_color_is_hex(self, effect):
        color = EFFECT_INFO[effect]['color']
        assert color.startswith('#')
        assert len(color) == 7


class TestStructureGroups:
    """Validate STRUCTURE_GROUPS constant."""

    def test_citadel_group(self):
        assert STRUCTURE_GROUPS[1657] == 'Citadel'

    def test_engineering_group(self):
        assert STRUCTURE_GROUPS[1406] == 'Engineering'

    def test_refinery_group(self):
        assert STRUCTURE_GROUPS[1404] == 'Refinery'

    def test_pos_group(self):
        assert STRUCTURE_GROUPS[365] == 'POS'

    def test_four_structure_groups(self):
        assert len(STRUCTURE_GROUPS) == 4


class TestShipClassConstants:
    """Validate SHIP_CLASSES constant."""

    def test_all_categories_present(self):
        expected = {'capital', 'battleship', 'cruiser', 'destroyer', 'frigate'}
        assert set(SHIP_CLASSES.keys()) == expected

    def test_capitals_include_titans(self):
        caps = SHIP_CLASSES['capital']
        for titan in ['Avatar', 'Erebus', 'Ragnarok', 'Leviathan']:
            assert titan in caps, f"{titan} missing from capitals"

    def test_capitals_include_dreads(self):
        caps = SHIP_CLASSES['capital']
        for dread in ['Revelation', 'Naglfar', 'Moros', 'Phoenix']:
            assert dread in caps, f"{dread} missing from capitals"

    def test_no_duplicate_ships_across_categories(self):
        """Each ship name should appear in only one category."""
        all_ships = []
        for ships in SHIP_CLASSES.values():
            all_ships.extend(ships)
        assert len(all_ships) == len(set(all_ships)), "Duplicate ships found across categories"


class TestThreatShips:
    """Validate THREAT_SHIPS constant."""

    def test_threat_ships_is_set(self):
        assert isinstance(THREAT_SHIPS, set)

    def test_interdictors_are_threats(self):
        for dictor in ['Sabre', 'Flycatcher', 'Heretic', 'Eris']:
            assert dictor in THREAT_SHIPS, f"{dictor} should be a threat ship"

    def test_recon_ships_are_threats(self):
        for recon in ['Lachesis', 'Arazu', 'Huginn', 'Rapier', 'Falcon', 'Rook']:
            assert recon in THREAT_SHIPS, f"{recon} should be a threat ship"

    def test_t3_cruisers_are_threats(self):
        for t3 in ['Proteus', 'Loki', 'Tengu', 'Legion']:
            assert t3 in THREAT_SHIPS, f"{t3} should be a threat ship"

    def test_stratios_is_threat(self):
        assert 'Stratios' in THREAT_SHIPS


# ---------------------------------------------------------------------------
# _classify_ships pure function
# ---------------------------------------------------------------------------

class TestClassifyShips:
    """Test OpportunityScorer._classify_ships() method."""

    def setup_method(self):
        # Instantiate without DB (we only call the pure method)
        self.scorer = OpportunityScorer()

    def test_empty_list(self):
        result = self.scorer._classify_ships([])
        assert result == {
            'capital': [], 'battleship': [], 'cruiser': [],
            'destroyer': [], 'frigate': [], 'other': [], 'threats': [],
        }

    def test_none_entries_skipped(self):
        result = self.scorer._classify_ships([None, '', None])
        for key in result:
            assert result[key] == []

    def test_single_capital(self):
        result = self.scorer._classify_ships(['Naglfar'])
        assert 'Naglfar' in result['capital']

    def test_single_frigate(self):
        result = self.scorer._classify_ships(['Merlin'])
        assert 'Merlin' in result['frigate']

    def test_single_battleship(self):
        result = self.scorer._classify_ships(['Raven'])
        assert 'Raven' in result['battleship']

    def test_single_cruiser(self):
        result = self.scorer._classify_ships(['Cerberus'])
        assert 'Cerberus' in result['cruiser']

    def test_single_destroyer(self):
        result = self.scorer._classify_ships(['Sabre'])
        assert 'Sabre' in result['destroyer']
        # Sabre is also a threat ship
        assert 'Sabre' in result['threats']

    def test_threat_ship_dual_classification(self):
        """Threat ships should appear in both 'threats' and their category."""
        result = self.scorer._classify_ships(['Loki'])
        assert 'Loki' in result['threats']
        assert 'Loki' in result['cruiser']

    def test_capsule_not_classified(self):
        result = self.scorer._classify_ships(['Capsule'])
        assert result['other'] == []

    def test_shuttle_not_classified(self):
        result = self.scorer._classify_ships(['Shuttle'])
        assert result['other'] == []

    def test_unknown_ship_goes_to_other(self):
        result = self.scorer._classify_ships(['MysteryShip9000'])
        assert 'MysteryShip9000' in result['other']

    def test_mixed_fleet(self):
        fleet = ['Naglfar', 'Cerberus', 'Sabre', 'Merlin', 'UnknownShip']
        result = self.scorer._classify_ships(fleet)
        assert 'Naglfar' in result['capital']
        assert 'Cerberus' in result['cruiser']
        assert 'Sabre' in result['destroyer']
        assert 'Sabre' in result['threats']
        assert 'Merlin' in result['frigate']
        assert 'UnknownShip' in result['other']

    @pytest.mark.parametrize("ship,expected_category", [
        ('Apostle', 'capital'),
        ('Leshak', 'battleship'),
        ('Gila', 'cruiser'),
        ('Jackdaw', 'destroyer'),
        ('Astero', 'frigate'),
    ])
    def test_specific_ship_classification(self, ship, expected_category):
        result = self.scorer._classify_ships([ship])
        assert ship in result[expected_category]

    @pytest.mark.parametrize("threat_ship", list(THREAT_SHIPS))
    def test_all_threat_ships_detected(self, threat_ship):
        result = self.scorer._classify_ships([threat_ship])
        assert threat_ship in result['threats']

    def test_substring_match_works(self):
        """The classifier uses 'any(s in ship for s in ships)' — verify substring matching."""
        # "Naglfar Fleet Issue" would match 'Naglfar' via substring
        result = self.scorer._classify_ships(['Naglfar Fleet Issue'])
        assert 'Naglfar Fleet Issue' in result['capital']
