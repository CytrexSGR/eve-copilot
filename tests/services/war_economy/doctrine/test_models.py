import pytest
from datetime import datetime
from services.war_economy.doctrine.models import (
    FleetSnapshot,
    DoctrineTemplate,
    ItemOfInterest,
    ShipEntry
)


class TestFleetSnapshot:
    """Test FleetSnapshot data model."""

    def test_fleet_snapshot_creation(self):
        """Test creating a fleet snapshot with valid data."""
        snapshot = FleetSnapshot(
            id=1,
            timestamp=datetime(2026, 1, 14, 12, 0, 0),
            system_id=30000142,  # Jita
            region_id=10000002,  # The Forge
            ships=[
                ShipEntry(type_id=11190, count=12),  # Machariel
                ShipEntry(type_id=638, count=8)       # Loki
            ],
            total_pilots=20,
            killmail_ids=[123456, 123457, 123458],
            created_at=datetime.now()
        )

        assert snapshot.id == 1
        assert snapshot.system_id == 30000142
        assert len(snapshot.ships) == 2
        assert snapshot.ships[0].type_id == 11190
        assert snapshot.ships[0].count == 12
        assert len(snapshot.killmail_ids) == 3

    def test_normalize_vector(self):
        """Test vector normalization for cosine similarity."""
        snapshot = FleetSnapshot(
            id=1,
            timestamp=datetime.now(),
            system_id=30000142,
            region_id=10000002,
            ships=[
                ShipEntry(type_id=11190, count=12),  # 60% Machariel
                ShipEntry(type_id=638, count=8)       # 40% Loki
            ],
            total_pilots=20,
            killmail_ids=[],
            created_at=datetime.now()
        )

        normalized = snapshot.normalize_vector()

        # Step 1: Proportions are 12/20=0.6, 8/20=0.4
        # Step 2: Magnitude = sqrt(0.6^2 + 0.4^2) = sqrt(0.52) ≈ 0.7211
        # Step 3: Unit vector = (0.6/0.7211, 0.4/0.7211) ≈ (0.832, 0.555)
        assert normalized["11190"] == pytest.approx(0.832, abs=0.01)
        assert normalized["638"] == pytest.approx(0.555, abs=0.01)
        # Vector magnitude should be 1.0 for normalized vectors
        magnitude = sum(v**2 for v in normalized.values()) ** 0.5
        assert magnitude == pytest.approx(1.0)


class TestDoctrineTemplate:
    """Test DoctrineTemplate data model."""

    def test_doctrine_creation(self):
        """Test creating a doctrine template."""
        doctrine = DoctrineTemplate(
            id=1,
            doctrine_name="Machariel Doctrine",
            alliance_id=99003214,  # Goonswarm
            region_id=10000054,  # Fountain
            composition={"11190": 0.6, "638": 0.4},  # Normalized
            confidence_score=0.85,
            observation_count=15,
            first_seen=datetime(2026, 1, 10, 0, 0, 0),
            last_seen=datetime(2026, 1, 14, 12, 0, 0),
            total_pilots_avg=18,
            primary_doctrine_type="subcap",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        assert doctrine.doctrine_name == "Machariel Doctrine"
        assert doctrine.confidence_score == 0.85
        assert doctrine.primary_doctrine_type == "subcap"

    def test_update_from_snapshot(self):
        """Test updating doctrine from new snapshot observation."""
        doctrine = DoctrineTemplate(
            id=1,
            doctrine_name="Machariel Doctrine",
            composition={"11190": 0.6, "638": 0.4},
            confidence_score=0.68,  # Initial: 1 - (1/sqrt(10)) ≈ 0.68
            observation_count=10,
            first_seen=datetime(2026, 1, 10, 0, 0, 0),
            last_seen=datetime(2026, 1, 13, 0, 0, 0),
            total_pilots_avg=18,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # New snapshot with similar composition
        new_composition = {"11190": 0.65, "638": 0.35}
        new_timestamp = datetime(2026, 1, 14, 12, 0, 0)

        doctrine.update_from_observation(
            composition=new_composition,
            timestamp=new_timestamp,
            pilot_count=20
        )

        # Observation count should increment
        assert doctrine.observation_count == 11
        # Last seen should update
        assert doctrine.last_seen == new_timestamp
        # Composition should be rolling average (weighted)
        # 70% existing (0.6) + 30% new (0.65) = 0.615
        assert doctrine.composition["11190"] == pytest.approx(0.615, abs=0.01)
        # Confidence should increase with more observations
        # New: 1 - (1/sqrt(11)) ≈ 0.698
        assert doctrine.confidence_score > 0.68
        assert doctrine.confidence_score == pytest.approx(0.698, abs=0.01)


class TestItemOfInterest:
    """Test ItemOfInterest data model."""

    def test_item_creation(self):
        """Test creating an item of interest."""
        item = ItemOfInterest(
            id=1,
            doctrine_id=1,
            type_id=2048,  # Republic Fleet EMP M
            item_name="Republic Fleet EMP M",
            item_category="ammunition",
            consumption_rate=15000.0,  # rounds per hour
            priority=1,  # Critical
            created_at=datetime.now()
        )

        assert item.doctrine_id == 1
        assert item.item_category == "ammunition"
        assert item.priority == 1

    def test_item_priority_validation(self):
        """Test that priority must be 1-3."""
        with pytest.raises(ValueError, match="Priority must be between 1 and 3"):
            ItemOfInterest(
                id=1,
                doctrine_id=1,
                type_id=2048,
                item_name="Test Item",
                item_category="ammunition",
                priority=5,  # Invalid
                created_at=datetime.now()
            )
