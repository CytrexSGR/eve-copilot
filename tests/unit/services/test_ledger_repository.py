"""Tests for production ledger repository."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch


@pytest.fixture
def mock_db_pool():
    """Mock database pool."""
    pool = Mock()
    conn = Mock()
    cursor = Mock()

    # Setup cursor to use RealDictCursor-like behavior
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=None)

    conn.__enter__ = Mock(return_value=conn)
    conn.__exit__ = Mock(return_value=None)
    conn.cursor = Mock(return_value=cursor)

    pool.get_connection = Mock(return_value=conn)
    pool.get_connection.__enter__ = Mock(return_value=conn)
    pool.get_connection.__exit__ = Mock(return_value=None)

    return pool, conn, cursor


class TestLedgerRepositoryCreate:
    """Tests for creating ledgers."""

    def test_create_ledger_minimal(self, mock_db_pool):
        """Test creating ledger with minimal fields."""
        from src.services.production.ledger_repository import LedgerRepository
        from src.services.production.ledger_models import LedgerCreate

        pool, conn, cursor = mock_db_pool
        now = datetime.now()

        cursor.fetchone.return_value = {
            "id": 1,
            "character_id": 123456,
            "name": "Test Project",
            "target_type_id": None,
            "target_type_name": None,
            "target_quantity": 1,
            "status": "planning",
            "tax_profile_id": None,
            "facility_id": None,
            "total_material_cost": 0,
            "total_job_cost": 0,
            "total_cost": 0,
            "expected_revenue": 0,
            "expected_profit": 0,
            "started_at": None,
            "completed_at": None,
            "created_at": now,
            "updated_at": now
        }

        repo = LedgerRepository(pool)
        data = LedgerCreate(character_id=123456, name="Test Project")
        result = repo.create(data)

        assert result["id"] == 1
        assert result["character_id"] == 123456
        assert result["name"] == "Test Project"
        assert result["status"] == "planning"
        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()

    def test_create_ledger_full(self, mock_db_pool):
        """Test creating ledger with all fields."""
        from src.services.production.ledger_repository import LedgerRepository
        from src.services.production.ledger_models import LedgerCreate

        pool, conn, cursor = mock_db_pool
        now = datetime.now()

        cursor.fetchone.return_value = {
            "id": 1,
            "character_id": 123456,
            "name": "Revelation Build",
            "target_type_id": 19720,
            "target_type_name": None,
            "target_quantity": 5,
            "status": "planning",
            "tax_profile_id": 1,
            "facility_id": 2,
            "total_material_cost": 0,
            "total_job_cost": 0,
            "total_cost": 0,
            "expected_revenue": 0,
            "expected_profit": 0,
            "started_at": None,
            "completed_at": None,
            "created_at": now,
            "updated_at": now
        }

        repo = LedgerRepository(pool)
        data = LedgerCreate(
            character_id=123456,
            name="Revelation Build",
            target_type_id=19720,
            target_quantity=5,
            tax_profile_id=1,
            facility_id=2
        )
        result = repo.create(data)

        assert result["id"] == 1
        assert result["target_type_id"] == 19720
        assert result["target_quantity"] == 5


class TestLedgerRepositoryGetById:
    """Tests for getting ledger by ID."""

    def test_get_by_id_found(self, mock_db_pool):
        """Test getting existing ledger."""
        from src.services.production.ledger_repository import LedgerRepository

        pool, conn, cursor = mock_db_pool
        now = datetime.now()

        cursor.fetchone.return_value = {
            "id": 1,
            "character_id": 123456,
            "name": "Test Project",
            "target_type_id": None,
            "target_type_name": None,
            "target_quantity": 1,
            "status": "planning",
            "tax_profile_id": None,
            "facility_id": None,
            "total_material_cost": 0,
            "total_job_cost": 0,
            "total_cost": 0,
            "expected_revenue": 0,
            "expected_profit": 0,
            "started_at": None,
            "completed_at": None,
            "created_at": now,
            "updated_at": now
        }

        repo = LedgerRepository(pool)
        result = repo.get_by_id(1)

        assert result is not None
        assert result["id"] == 1
        assert result["name"] == "Test Project"

    def test_get_by_id_not_found(self, mock_db_pool):
        """Test getting non-existent ledger."""
        from src.services.production.ledger_repository import LedgerRepository

        pool, conn, cursor = mock_db_pool
        cursor.fetchone.return_value = None

        repo = LedgerRepository(pool)
        result = repo.get_by_id(999)

        assert result is None


class TestLedgerRepositoryGetByCharacter:
    """Tests for getting ledgers by character."""

    def test_get_by_character(self, mock_db_pool):
        """Test getting ledgers for a character."""
        from src.services.production.ledger_repository import LedgerRepository

        pool, conn, cursor = mock_db_pool
        now = datetime.now()

        cursor.fetchall.return_value = [
            {
                "id": 1,
                "character_id": 123456,
                "name": "Project 1",
                "target_type_id": None,
                "target_type_name": None,
                "target_quantity": 1,
                "status": "planning",
                "tax_profile_id": None,
                "facility_id": None,
                "total_material_cost": 0,
                "total_job_cost": 0,
                "total_cost": 0,
                "expected_revenue": 0,
                "expected_profit": 0,
                "started_at": None,
                "completed_at": None,
                "created_at": now,
                "updated_at": now
            },
            {
                "id": 2,
                "character_id": 123456,
                "name": "Project 2",
                "target_type_id": 19720,
                "target_type_name": "Revelation",
                "target_quantity": 5,
                "status": "active",
                "tax_profile_id": 1,
                "facility_id": 2,
                "total_material_cost": 5000000000,
                "total_job_cost": 100000000,
                "total_cost": 5100000000,
                "expected_revenue": 6000000000,
                "expected_profit": 900000000,
                "started_at": now,
                "completed_at": None,
                "created_at": now,
                "updated_at": now
            }
        ]

        repo = LedgerRepository(pool)
        result = repo.get_by_character(123456)

        assert len(result) == 2
        assert result[0]["name"] == "Project 1"
        assert result[1]["name"] == "Project 2"

    def test_get_by_character_empty(self, mock_db_pool):
        """Test getting ledgers for character with none."""
        from src.services.production.ledger_repository import LedgerRepository

        pool, conn, cursor = mock_db_pool
        cursor.fetchall.return_value = []

        repo = LedgerRepository(pool)
        result = repo.get_by_character(123456)

        assert result == []


class TestLedgerRepositoryUpdate:
    """Tests for updating ledgers."""

    def test_update_name(self, mock_db_pool):
        """Test updating ledger name."""
        from src.services.production.ledger_repository import LedgerRepository
        from src.services.production.ledger_models import LedgerUpdate

        pool, conn, cursor = mock_db_pool
        now = datetime.now()

        cursor.fetchone.return_value = {
            "id": 1,
            "character_id": 123456,
            "name": "Updated Name",
            "target_type_id": None,
            "target_type_name": None,
            "target_quantity": 1,
            "status": "planning",
            "tax_profile_id": None,
            "facility_id": None,
            "total_material_cost": 0,
            "total_job_cost": 0,
            "total_cost": 0,
            "expected_revenue": 0,
            "expected_profit": 0,
            "started_at": None,
            "completed_at": None,
            "created_at": now,
            "updated_at": now
        }

        repo = LedgerRepository(pool)
        result = repo.update(1, LedgerUpdate(name="Updated Name"))

        assert result is not None
        assert result["name"] == "Updated Name"

    def test_update_status(self, mock_db_pool):
        """Test updating ledger status."""
        from src.services.production.ledger_repository import LedgerRepository
        from src.services.production.ledger_models import LedgerUpdate

        pool, conn, cursor = mock_db_pool
        now = datetime.now()

        cursor.fetchone.return_value = {
            "id": 1,
            "character_id": 123456,
            "name": "Test",
            "target_type_id": None,
            "target_type_name": None,
            "target_quantity": 1,
            "status": "active",
            "tax_profile_id": None,
            "facility_id": None,
            "total_material_cost": 0,
            "total_job_cost": 0,
            "total_cost": 0,
            "expected_revenue": 0,
            "expected_profit": 0,
            "started_at": None,
            "completed_at": None,
            "created_at": now,
            "updated_at": now
        }

        repo = LedgerRepository(pool)
        result = repo.update(1, LedgerUpdate(status="active"))

        assert result is not None
        assert result["status"] == "active"

    def test_update_not_found(self, mock_db_pool):
        """Test updating non-existent ledger."""
        from src.services.production.ledger_repository import LedgerRepository
        from src.services.production.ledger_models import LedgerUpdate

        pool, conn, cursor = mock_db_pool
        cursor.fetchone.return_value = None

        repo = LedgerRepository(pool)
        result = repo.update(999, LedgerUpdate(name="Test"))

        assert result is None


class TestLedgerRepositoryDelete:
    """Tests for deleting ledgers."""

    def test_delete_success(self, mock_db_pool):
        """Test successful deletion."""
        from src.services.production.ledger_repository import LedgerRepository

        pool, conn, cursor = mock_db_pool
        cursor.rowcount = 1

        repo = LedgerRepository(pool)
        result = repo.delete(1)

        assert result is True
        conn.commit.assert_called_once()

    def test_delete_not_found(self, mock_db_pool):
        """Test deleting non-existent ledger."""
        from src.services.production.ledger_repository import LedgerRepository

        pool, conn, cursor = mock_db_pool
        cursor.rowcount = 0

        repo = LedgerRepository(pool)
        result = repo.delete(999)

        assert result is False


class TestLedgerRepositoryStages:
    """Tests for stage operations."""

    def test_add_stage(self, mock_db_pool):
        """Test adding a stage to ledger."""
        from src.services.production.ledger_repository import LedgerRepository
        from src.services.production.ledger_models import StageCreate

        pool, conn, cursor = mock_db_pool
        now = datetime.now()

        cursor.fetchone.return_value = {
            "id": 1,
            "ledger_id": 10,
            "name": "Component Manufacturing",
            "stage_order": 1,
            "status": "pending",
            "material_cost": 0,
            "job_cost": 0,
            "completed_at": None,
            "created_at": now,
            "updated_at": now
        }

        repo = LedgerRepository(pool)
        data = StageCreate(name="Component Manufacturing", stage_order=1)
        result = repo.add_stage(10, data)

        assert result["id"] == 1
        assert result["ledger_id"] == 10
        assert result["name"] == "Component Manufacturing"
        assert result["stage_order"] == 1
        conn.commit.assert_called_once()

    def test_get_stages(self, mock_db_pool):
        """Test getting stages for a ledger."""
        from src.services.production.ledger_repository import LedgerRepository

        pool, conn, cursor = mock_db_pool
        now = datetime.now()

        cursor.fetchall.return_value = [
            {
                "id": 1,
                "ledger_id": 10,
                "name": "Components",
                "stage_order": 1,
                "status": "pending",
                "material_cost": 0,
                "job_cost": 0,
                "completed_at": None,
                "created_at": now,
                "updated_at": now
            },
            {
                "id": 2,
                "ledger_id": 10,
                "name": "Assembly",
                "stage_order": 2,
                "status": "pending",
                "material_cost": 0,
                "job_cost": 0,
                "completed_at": None,
                "created_at": now,
                "updated_at": now
            }
        ]

        repo = LedgerRepository(pool)
        result = repo.get_stages(10)

        assert len(result) == 2
        assert result[0]["stage_order"] == 1
        assert result[1]["stage_order"] == 2

    def test_update_stage(self, mock_db_pool):
        """Test updating a stage."""
        from src.services.production.ledger_repository import LedgerRepository
        from src.services.production.ledger_models import StageUpdate

        pool, conn, cursor = mock_db_pool
        now = datetime.now()

        cursor.fetchone.return_value = {
            "id": 1,
            "ledger_id": 10,
            "name": "Components",
            "stage_order": 1,
            "status": "in_progress",
            "material_cost": 0,
            "job_cost": 0,
            "completed_at": None,
            "created_at": now,
            "updated_at": now
        }

        repo = LedgerRepository(pool)
        result = repo.update_stage(1, StageUpdate(status="in_progress"))

        assert result is not None
        assert result["status"] == "in_progress"


class TestLedgerRepositoryJobs:
    """Tests for job operations."""

    def test_add_job(self, mock_db_pool):
        """Test adding a job to stage."""
        from src.services.production.ledger_repository import LedgerRepository
        from src.services.production.ledger_models import JobCreate

        pool, conn, cursor = mock_db_pool
        now = datetime.now()

        cursor.fetchone.return_value = {
            "id": 1,
            "ledger_id": 10,
            "stage_id": 5,
            "type_id": 19720,
            "type_name": None,
            "blueprint_type_id": None,
            "quantity": 1,
            "runs": 1,
            "me_level": 10,
            "te_level": 20,
            "facility_id": None,
            "material_cost": 0,
            "job_cost": 0,
            "production_time": 0,
            "status": "pending",
            "esi_job_id": None,
            "started_at": None,
            "completed_at": None,
            "created_at": now
        }

        repo = LedgerRepository(pool)
        data = JobCreate(type_id=19720, quantity=1, runs=1, me_level=10, te_level=20)
        result = repo.add_job(10, 5, data)

        assert result["id"] == 1
        assert result["type_id"] == 19720
        assert result["me_level"] == 10
        conn.commit.assert_called_once()

    def test_get_jobs(self, mock_db_pool):
        """Test getting jobs for a stage."""
        from src.services.production.ledger_repository import LedgerRepository

        pool, conn, cursor = mock_db_pool
        now = datetime.now()

        cursor.fetchall.return_value = [
            {
                "id": 1,
                "ledger_id": 10,
                "stage_id": 5,
                "type_id": 19720,
                "type_name": "Revelation",
                "blueprint_type_id": 19721,
                "quantity": 1,
                "runs": 1,
                "me_level": 10,
                "te_level": 20,
                "facility_id": 2,
                "material_cost": 5000000000,
                "job_cost": 100000000,
                "production_time": 86400,
                "status": "pending",
                "esi_job_id": None,
                "started_at": None,
                "completed_at": None,
                "created_at": now
            }
        ]

        repo = LedgerRepository(pool)
        result = repo.get_jobs(5)

        assert len(result) == 1
        assert result[0]["type_name"] == "Revelation"


class TestLedgerRepositoryMaterials:
    """Tests for material operations."""

    def test_upsert_material_insert(self, mock_db_pool):
        """Test inserting a new material."""
        from src.services.production.ledger_repository import LedgerRepository
        from src.services.production.ledger_models import MaterialUpsert

        pool, conn, cursor = mock_db_pool

        cursor.fetchone.return_value = {
            "id": 1,
            "ledger_id": 10,
            "type_id": 34,
            "type_name": "Tritanium",
            "total_needed": 1000000,
            "total_acquired": 0,
            "estimated_cost": 500000000,
            "source": "buy"
        }

        repo = LedgerRepository(pool)
        data = MaterialUpsert(
            type_id=34,
            type_name="Tritanium",
            total_needed=1000000,
            estimated_cost=500000000,
            source="buy"
        )
        result = repo.upsert_material(10, data)

        assert result["type_id"] == 34
        assert result["total_needed"] == 1000000
        conn.commit.assert_called_once()

    def test_get_materials(self, mock_db_pool):
        """Test getting materials for a ledger."""
        from src.services.production.ledger_repository import LedgerRepository

        pool, conn, cursor = mock_db_pool

        cursor.fetchall.return_value = [
            {
                "id": 1,
                "ledger_id": 10,
                "type_id": 34,
                "type_name": "Tritanium",
                "total_needed": 1000000,
                "total_acquired": 500000,
                "estimated_cost": 500000000,
                "source": "buy"
            },
            {
                "id": 2,
                "ledger_id": 10,
                "type_id": 35,
                "type_name": "Pyerite",
                "total_needed": 200000,
                "total_acquired": 100000,
                "estimated_cost": 100000000,
                "source": "buy"
            }
        ]

        repo = LedgerRepository(pool)
        result = repo.get_materials(10)

        assert len(result) == 2
        assert result[0]["type_name"] == "Tritanium"
        assert result[1]["type_name"] == "Pyerite"


class TestLedgerRepositoryGetWithDetails:
    """Tests for getting ledger with nested details."""

    def test_get_with_details(self, mock_db_pool):
        """Test getting ledger with stages and materials."""
        from src.services.production.ledger_repository import LedgerRepository

        pool, conn, cursor = mock_db_pool
        now = datetime.now()

        # Setup multiple fetchone/fetchall returns
        ledger_data = {
            "id": 1,
            "character_id": 123456,
            "name": "Test Project",
            "target_type_id": 19720,
            "target_type_name": "Revelation",
            "target_quantity": 1,
            "status": "active",
            "tax_profile_id": 1,
            "facility_id": 2,
            "total_material_cost": 5000000000,
            "total_job_cost": 100000000,
            "total_cost": 5100000000,
            "expected_revenue": 6000000000,
            "expected_profit": 900000000,
            "started_at": now,
            "completed_at": None,
            "created_at": now,
            "updated_at": now
        }

        stages_data = [
            {
                "id": 1,
                "ledger_id": 1,
                "name": "Components",
                "stage_order": 1,
                "status": "completed",
                "material_cost": 1000000000,
                "job_cost": 50000000,
                "completed_at": now,
                "created_at": now,
                "updated_at": now
            }
        ]

        jobs_data = [
            {
                "id": 1,
                "ledger_id": 1,
                "stage_id": 1,
                "type_id": 11186,
                "type_name": "Capital Armor Plates",
                "blueprint_type_id": 11187,
                "quantity": 10,
                "runs": 10,
                "me_level": 10,
                "te_level": 20,
                "facility_id": 2,
                "material_cost": 100000000,
                "job_cost": 5000000,
                "production_time": 3600,
                "status": "completed",
                "esi_job_id": 123456789,
                "started_at": now,
                "completed_at": now,
                "created_at": now
            }
        ]

        materials_data = [
            {
                "id": 1,
                "ledger_id": 1,
                "type_id": 34,
                "type_name": "Tritanium",
                "total_needed": 1000000,
                "total_acquired": 1000000,
                "estimated_cost": 500000000,
                "source": "buy"
            }
        ]

        # Mock the cursor to return different results for different queries
        cursor.fetchone.return_value = ledger_data
        cursor.fetchall.side_effect = [stages_data, jobs_data, materials_data]

        repo = LedgerRepository(pool)
        result = repo.get_with_details(1)

        assert result is not None
        assert result["id"] == 1
        assert "stages" in result
        assert len(result["stages"]) == 1
        assert result["stages"][0]["name"] == "Components"
        assert "jobs" in result["stages"][0]
        assert len(result["stages"][0]["jobs"]) == 1
        assert "materials" in result
        assert len(result["materials"]) == 1
