# tests/unit/services/test_doctrine_clustering.py
"""Unit tests for doctrine clustering."""

import pytest
import hashlib


class TestFittingHasher:
    def test_hash_identical_fittings_same(self):
        from src.services.doctrine.clustering import FittingHasher

        hasher = FittingHasher()

        items1 = [
            {"type_id": 100, "flag": "HiSlot0"},
            {"type_id": 200, "flag": "MedSlot0"},
        ]
        items2 = [
            {"type_id": 100, "flag": "HiSlot0"},
            {"type_id": 200, "flag": "MedSlot0"},
        ]

        hash1 = hasher.hash_fitting(ship_type_id=1, items=items1)
        hash2 = hasher.hash_fitting(ship_type_id=1, items=items2)

        assert hash1 == hash2

    def test_hash_different_ships_different(self):
        from src.services.doctrine.clustering import FittingHasher

        hasher = FittingHasher()

        items = [{"type_id": 100, "flag": "HiSlot0"}]

        hash1 = hasher.hash_fitting(ship_type_id=1, items=items)
        hash2 = hasher.hash_fitting(ship_type_id=2, items=items)

        assert hash1 != hash2


class TestDoctrineClustering:
    def test_create_feature_vector(self):
        from src.services.doctrine.clustering import DoctrineClustering
        from src.services.battle_report.models import KillmailFittingAnalysis

        clustering = DoctrineClustering()

        fitting = KillmailFittingAnalysis(
            killmail_id=1,
            ship_type_id=37480,
            ship_name="Ferox",
            tank_type="shield",
            weapon_type="railgun",
            high_slots=6,
            med_slots=5,
            low_slots=4,
            rig_slots=2
        )

        vector = clustering._create_feature_vector(fitting)

        assert len(vector) > 0
        assert isinstance(vector, list)

    def test_cluster_similar_fittings(self):
        from src.services.doctrine.clustering import DoctrineClustering
        from src.services.battle_report.models import KillmailFittingAnalysis

        clustering = DoctrineClustering()

        # 5 similar Ferox fittings (same doctrine)
        fittings = [
            KillmailFittingAnalysis(
                killmail_id=i,
                ship_type_id=37480,
                ship_name="Ferox",
                tank_type="shield",
                weapon_type="railgun",
                high_slots=6,
                med_slots=5,
                low_slots=4,
                rig_slots=2
            )
            for i in range(5)
        ]

        # Add one different fitting
        fittings.append(KillmailFittingAnalysis(
            killmail_id=99,
            ship_type_id=24690,  # Hurricane
            ship_name="Hurricane",
            tank_type="armor",
            weapon_type="autocannon",
            high_slots=6,
            med_slots=4,
            low_slots=6,
            rig_slots=3
        ))

        clusters = clustering.cluster_fittings(fittings)

        # Should have clusters
        assert len(clusters) >= 1
