"""Tests for production ledger service business logic."""

import pytest
from datetime import datetime
from unittest.mock import Mock


@pytest.fixture
def mock_repository():
    """Mock ledger repository."""
    return Mock()


@pytest.fixture
def mock_market_service():
    """Mock market service."""
    return Mock()


class TestLedgerServiceCreate:
    """Tests for creating ledgers."""

    def test_create_ledger(self, mock_repository, mock_market_service):
        """Test creating a new ledger."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import LedgerCreate, Ledger

        now = datetime.now()
        mock_repository.create.return_value = {
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

        service = LedgerService(mock_repository, mock_market_service)
        data = LedgerCreate(character_id=123456, name="Test Project")
        result = service.create_ledger(data)

        assert isinstance(result, Ledger)
        assert result.id == 1
        assert result.name == "Test Project"
        assert result.status == "planning"
        mock_repository.create.assert_called_once_with(data)


class TestLedgerServiceGet:
    """Tests for getting ledgers."""

    def test_get_ledger_found(self, mock_repository, mock_market_service):
        """Test getting an existing ledger."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import Ledger

        now = datetime.now()
        mock_repository.get_by_id.return_value = {
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

        service = LedgerService(mock_repository, mock_market_service)
        result = service.get_ledger(1)

        assert isinstance(result, Ledger)
        assert result.id == 1

    def test_get_ledger_not_found(self, mock_repository, mock_market_service):
        """Test getting a non-existent ledger raises error."""
        from src.services.production.ledger_service import LedgerService
        from src.core.exceptions import NotFoundError

        mock_repository.get_by_id.return_value = None

        service = LedgerService(mock_repository, mock_market_service)

        with pytest.raises(NotFoundError) as exc_info:
            service.get_ledger(999)

        assert exc_info.value.resource == "Ledger"
        assert exc_info.value.resource_id == 999

    def test_get_ledgers_by_character(self, mock_repository, mock_market_service):
        """Test getting all ledgers for a character."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import Ledger

        now = datetime.now()
        mock_repository.get_by_character.return_value = [
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

        service = LedgerService(mock_repository, mock_market_service)
        result = service.get_ledgers_by_character(123456)

        assert len(result) == 2
        assert all(isinstance(l, Ledger) for l in result)
        assert result[0].name == "Project 1"
        assert result[1].name == "Project 2"


class TestLedgerServiceUpdate:
    """Tests for updating ledgers."""

    def test_update_ledger(self, mock_repository, mock_market_service):
        """Test updating a ledger."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import LedgerUpdate, Ledger

        now = datetime.now()
        mock_repository.update.return_value = {
            "id": 1,
            "character_id": 123456,
            "name": "Updated Name",
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

        service = LedgerService(mock_repository, mock_market_service)
        result = service.update_ledger(1, LedgerUpdate(name="Updated Name", status="active"))

        assert isinstance(result, Ledger)
        assert result.name == "Updated Name"
        assert result.status == "active"

    def test_update_ledger_not_found(self, mock_repository, mock_market_service):
        """Test updating a non-existent ledger raises error."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import LedgerUpdate
        from src.core.exceptions import NotFoundError

        mock_repository.update.return_value = None

        service = LedgerService(mock_repository, mock_market_service)

        with pytest.raises(NotFoundError):
            service.update_ledger(999, LedgerUpdate(name="Test"))


class TestLedgerServiceDelete:
    """Tests for deleting ledgers."""

    def test_delete_ledger(self, mock_repository, mock_market_service):
        """Test deleting a ledger."""
        from src.services.production.ledger_service import LedgerService

        mock_repository.delete.return_value = True

        service = LedgerService(mock_repository, mock_market_service)
        result = service.delete_ledger(1)

        assert result is True
        mock_repository.delete.assert_called_once_with(1)

    def test_delete_ledger_not_found(self, mock_repository, mock_market_service):
        """Test deleting a non-existent ledger raises error."""
        from src.services.production.ledger_service import LedgerService
        from src.core.exceptions import NotFoundError

        mock_repository.delete.return_value = False

        service = LedgerService(mock_repository, mock_market_service)

        with pytest.raises(NotFoundError):
            service.delete_ledger(999)


class TestLedgerServiceStages:
    """Tests for stage operations."""

    def test_add_stage(self, mock_repository, mock_market_service):
        """Test adding a stage to a ledger."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import StageCreate, Stage

        now = datetime.now()
        mock_repository.get_by_id.return_value = {"id": 1}
        mock_repository.add_stage.return_value = {
            "id": 1,
            "ledger_id": 1,
            "name": "Component Manufacturing",
            "stage_order": 1,
            "status": "pending",
            "material_cost": 0,
            "job_cost": 0,
            "completed_at": None,
            "created_at": now,
            "updated_at": now
        }

        service = LedgerService(mock_repository, mock_market_service)
        data = StageCreate(name="Component Manufacturing", stage_order=1)
        result = service.add_stage(1, data)

        assert isinstance(result, Stage)
        assert result.name == "Component Manufacturing"
        assert result.stage_order == 1

    def test_add_stage_ledger_not_found(self, mock_repository, mock_market_service):
        """Test adding stage to non-existent ledger raises error."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import StageCreate
        from src.core.exceptions import NotFoundError

        mock_repository.get_by_id.return_value = None

        service = LedgerService(mock_repository, mock_market_service)
        data = StageCreate(name="Test", stage_order=1)

        with pytest.raises(NotFoundError):
            service.add_stage(999, data)

    def test_get_stages(self, mock_repository, mock_market_service):
        """Test getting stages for a ledger."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import Stage

        now = datetime.now()
        mock_repository.get_stages.return_value = [
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
            },
            {
                "id": 2,
                "ledger_id": 1,
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

        service = LedgerService(mock_repository, mock_market_service)
        result = service.get_stages(1)

        assert len(result) == 2
        assert all(isinstance(s, Stage) for s in result)
        assert result[0].stage_order == 1
        assert result[1].stage_order == 2


class TestLedgerServiceJobs:
    """Tests for job operations."""

    def test_add_job(self, mock_repository, mock_market_service):
        """Test adding a job to a stage."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import JobCreate, Job

        now = datetime.now()
        mock_repository._get_stage_by_id.return_value = {"id": 5, "ledger_id": 1}
        mock_repository.add_job.return_value = {
            "id": 1,
            "ledger_id": 1,
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

        service = LedgerService(mock_repository, mock_market_service)
        data = JobCreate(type_id=19720, quantity=1, runs=1, me_level=10, te_level=20)
        result = service.add_job(1, 5, data)

        assert isinstance(result, Job)
        assert result.type_id == 19720
        assert result.me_level == 10

    def test_add_job_stage_not_found(self, mock_repository, mock_market_service):
        """Test adding job to non-existent stage raises error."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import JobCreate
        from src.core.exceptions import NotFoundError

        mock_repository._get_stage_by_id.return_value = None

        service = LedgerService(mock_repository, mock_market_service)
        data = JobCreate(type_id=34, quantity=1000, runs=10)

        with pytest.raises(NotFoundError):
            service.add_job(1, 999, data)

    def test_get_jobs(self, mock_repository, mock_market_service):
        """Test getting jobs for a stage."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import Job

        now = datetime.now()
        mock_repository.get_jobs.return_value = [
            {
                "id": 1,
                "ledger_id": 1,
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

        service = LedgerService(mock_repository, mock_market_service)
        result = service.get_jobs(5)

        assert len(result) == 1
        assert isinstance(result[0], Job)
        assert result[0].type_name == "Revelation"


class TestLedgerServiceMaterials:
    """Tests for material operations."""

    def test_upsert_material(self, mock_repository, mock_market_service):
        """Test upserting a material."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import MaterialUpsert, Material

        mock_repository.get_by_id.return_value = {"id": 1}
        mock_repository.upsert_material.return_value = {
            "id": 1,
            "ledger_id": 1,
            "type_id": 34,
            "type_name": "Tritanium",
            "total_needed": 1000000,
            "total_acquired": 0,
            "estimated_cost": 500000000,
            "source": "buy"
        }

        service = LedgerService(mock_repository, mock_market_service)
        data = MaterialUpsert(
            type_id=34,
            type_name="Tritanium",
            total_needed=1000000,
            estimated_cost=500000000,
            source="buy"
        )
        result = service.upsert_material(1, data)

        assert isinstance(result, Material)
        assert result.type_name == "Tritanium"
        assert result.total_needed == 1000000

    def test_get_materials(self, mock_repository, mock_market_service):
        """Test getting materials for a ledger."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import Material

        mock_repository.get_materials.return_value = [
            {
                "id": 1,
                "ledger_id": 1,
                "type_id": 34,
                "type_name": "Tritanium",
                "total_needed": 1000000,
                "total_acquired": 500000,
                "estimated_cost": 500000000,
                "source": "buy"
            },
            {
                "id": 2,
                "ledger_id": 1,
                "type_id": 35,
                "type_name": "Pyerite",
                "total_needed": 200000,
                "total_acquired": 100000,
                "estimated_cost": 100000000,
                "source": "buy"
            }
        ]

        service = LedgerService(mock_repository, mock_market_service)
        result = service.get_materials(1)

        assert len(result) == 2
        assert all(isinstance(m, Material) for m in result)


class TestLedgerServiceGetWithDetails:
    """Tests for getting ledger with full details."""

    def test_get_with_details(self, mock_repository, mock_market_service):
        """Test getting ledger with all nested details."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import LedgerWithDetails

        now = datetime.now()
        mock_repository.get_with_details.return_value = {
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
            "updated_at": now,
            "stages": [
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
                    "updated_at": now,
                    "jobs": [
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
                }
            ],
            "materials": [
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
        }

        service = LedgerService(mock_repository, mock_market_service)
        result = service.get_ledger_with_details(1)

        assert isinstance(result, LedgerWithDetails)
        assert result.id == 1
        assert len(result.stages) == 1
        assert result.stages[0].name == "Components"
        assert len(result.stages[0].jobs) == 1
        assert len(result.materials) == 1

    def test_get_with_details_not_found(self, mock_repository, mock_market_service):
        """Test getting non-existent ledger with details raises error."""
        from src.services.production.ledger_service import LedgerService
        from src.core.exceptions import NotFoundError

        mock_repository.get_with_details.return_value = None

        service = LedgerService(mock_repository, mock_market_service)

        with pytest.raises(NotFoundError):
            service.get_ledger_with_details(999)


class TestLedgerServiceRecalculate:
    """Tests for cost recalculation."""

    def test_recalculate_costs(self, mock_repository, mock_market_service):
        """Test recalculating ledger costs."""
        from src.services.production.ledger_service import LedgerService
        from src.services.production.ledger_models import Ledger

        now = datetime.now()
        mock_repository.recalculate_costs.return_value = {
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

        service = LedgerService(mock_repository, mock_market_service)
        result = service.recalculate_costs(1)

        assert isinstance(result, Ledger)
        assert result.total_material_cost == 5000000000
        assert result.total_job_cost == 100000000
        assert result.total_cost == 5100000000
