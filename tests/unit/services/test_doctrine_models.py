# tests/unit/services/test_doctrine_models.py
"""Unit tests for doctrine models."""

import pytest
from datetime import datetime


class TestDoctrineTemplate:
    def test_create_template(self):
        from src.services.doctrine.models import DoctrineTemplate

        template = DoctrineTemplate(
            id=1,
            name="ferox_fleet",
            display_name="Ferox Fleet",
            ship_type_ids=[37480],
            weapon_group_ids=[74, 75],
            tank_type="shield",
            role="dps",
            engagement_range="long",
            typical_dps_range=(400, 500)
        )

        assert template.name == "ferox_fleet"
        assert 37480 in template.ship_type_ids
        assert template.role == "dps"


class TestDetectedDoctrine:
    def test_create_detected(self):
        from src.services.doctrine.models import DetectedDoctrine

        doctrine = DetectedDoctrine(
            alliance_id=99000001,
            doctrine_name="Ferox Fleet",
            is_known_doctrine=True,
            ship_type_id=37480,
            ship_name="Ferox",
            fit_hash="abc123",
            sightings=15,
            first_seen=datetime(2026, 1, 1),
            last_seen=datetime(2026, 1, 12),
            avg_dps=450.0,
            tank_type="shield",
            weapon_type="railgun",
            engagement_range="long",
            trend="stable"
        )

        assert doctrine.sightings == 15
        assert doctrine.trend == "stable"
        assert doctrine.alliance_id == 99000001


class TestFleetComposition:
    def test_create_fleet(self):
        from src.services.doctrine.models import FleetComposition

        fleet = FleetComposition(
            killmail_id=12345,
            primary_alliance_id=99000001,
            estimated_fleet_size=50,
            doctrine_mix=[{"name": "Ferox Fleet", "count": 40}],
            dps_count=40,
            logi_count=8,
            support_count=2,
            logi_ratio=0.16
        )

        assert fleet.estimated_fleet_size == 50
        assert fleet.logi_ratio == 0.16


class TestDoctrineMatchup:
    def test_create_matchup(self):
        from src.services.doctrine.models import DoctrineMatchup, DetectedDoctrine

        d1 = DetectedDoctrine(
            alliance_id=1, doctrine_name="A", is_known_doctrine=True,
            ship_type_id=1, ship_name="X", fit_hash="a",
            sightings=1, first_seen=datetime.now(), last_seen=datetime.now()
        )

        matchup = DoctrineMatchup(
            alliance1_id=1,
            alliance1_name="Alliance A",
            alliance1_doctrines=[d1],
            alliance2_id=2,
            alliance2_name="Alliance B",
            alliance2_doctrines=[],
            matchups=[],
            overall_advantage="alliance1",
            reasoning="More DPS"
        )

        assert matchup.overall_advantage == "alliance1"
