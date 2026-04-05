"""Tests for production ledger Pydantic models."""

import pytest
from datetime import datetime
from pydantic import ValidationError


class TestLedgerCreate:
    """Tests for LedgerCreate model."""

    def test_minimal_create(self):
        """Test creating ledger with minimal fields."""
        from src.services.production.ledger_models import LedgerCreate

        ledger = LedgerCreate(
            character_id=123456,
            name="Capital Ship Project"
        )

        assert ledger.character_id == 123456
        assert ledger.name == "Capital Ship Project"
        assert ledger.target_type_id is None
        assert ledger.target_quantity == 1
        assert ledger.tax_profile_id is None
        assert ledger.facility_id is None

    def test_full_create(self):
        """Test creating ledger with all fields."""
        from src.services.production.ledger_models import LedgerCreate

        ledger = LedgerCreate(
            character_id=123456,
            name="Revelation Build",
            target_type_id=19720,
            target_quantity=5,
            tax_profile_id=1,
            facility_id=2
        )

        assert ledger.character_id == 123456
        assert ledger.name == "Revelation Build"
        assert ledger.target_type_id == 19720
        assert ledger.target_quantity == 5
        assert ledger.tax_profile_id == 1
        assert ledger.facility_id == 2

    def test_name_required(self):
        """Test that name is required."""
        from src.services.production.ledger_models import LedgerCreate

        with pytest.raises(ValidationError) as exc_info:
            LedgerCreate(character_id=123456)

        assert "name" in str(exc_info.value)

    def test_character_id_required(self):
        """Test that character_id is required."""
        from src.services.production.ledger_models import LedgerCreate

        with pytest.raises(ValidationError) as exc_info:
            LedgerCreate(name="Test Project")

        assert "character_id" in str(exc_info.value)


class TestLedgerUpdate:
    """Tests for LedgerUpdate model."""

    def test_update_name_only(self):
        """Test updating only name."""
        from src.services.production.ledger_models import LedgerUpdate

        update = LedgerUpdate(name="New Project Name")

        assert update.name == "New Project Name"
        assert update.status is None

    def test_update_status_only(self):
        """Test updating only status."""
        from src.services.production.ledger_models import LedgerUpdate

        update = LedgerUpdate(status="active")

        assert update.name is None
        assert update.status == "active"

    def test_update_both_fields(self):
        """Test updating both fields."""
        from src.services.production.ledger_models import LedgerUpdate

        update = LedgerUpdate(name="Updated Name", status="completed")

        assert update.name == "Updated Name"
        assert update.status == "completed"

    def test_empty_update_allowed(self):
        """Test that empty update is allowed."""
        from src.services.production.ledger_models import LedgerUpdate

        update = LedgerUpdate()

        assert update.name is None
        assert update.status is None


class TestLedger:
    """Tests for Ledger response model."""

    def test_minimal_ledger(self):
        """Test ledger with minimal fields."""
        from src.services.production.ledger_models import Ledger

        now = datetime.now()
        ledger = Ledger(
            id=1,
            character_id=123456,
            name="Test Project",
            target_type_id=None,
            target_type_name=None,
            target_quantity=1,
            status="planning",
            tax_profile_id=None,
            facility_id=None,
            total_material_cost=0,
            total_job_cost=0,
            total_cost=0,
            expected_revenue=0,
            expected_profit=0,
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now
        )

        assert ledger.id == 1
        assert ledger.character_id == 123456
        assert ledger.name == "Test Project"
        assert ledger.status == "planning"
        assert ledger.total_cost == 0

    def test_full_ledger(self):
        """Test ledger with all fields populated."""
        from src.services.production.ledger_models import Ledger

        now = datetime.now()
        ledger = Ledger(
            id=1,
            character_id=123456,
            name="Revelation Build",
            target_type_id=19720,
            target_type_name="Revelation",
            target_quantity=5,
            status="active",
            tax_profile_id=1,
            facility_id=2,
            total_material_cost=5000000000,
            total_job_cost=100000000,
            total_cost=5100000000,
            expected_revenue=6000000000,
            expected_profit=900000000,
            started_at=now,
            completed_at=None,
            created_at=now,
            updated_at=now
        )

        assert ledger.id == 1
        assert ledger.target_type_name == "Revelation"
        assert ledger.total_material_cost == 5000000000
        assert ledger.expected_profit == 900000000


class TestStageCreate:
    """Tests for StageCreate model."""

    def test_stage_create(self):
        """Test creating a stage."""
        from src.services.production.ledger_models import StageCreate

        stage = StageCreate(
            name="Component Manufacturing",
            stage_order=1
        )

        assert stage.name == "Component Manufacturing"
        assert stage.stage_order == 1

    def test_stage_create_requires_name(self):
        """Test that name is required."""
        from src.services.production.ledger_models import StageCreate

        with pytest.raises(ValidationError) as exc_info:
            StageCreate(stage_order=1)

        assert "name" in str(exc_info.value)

    def test_stage_create_requires_order(self):
        """Test that stage_order is required."""
        from src.services.production.ledger_models import StageCreate

        with pytest.raises(ValidationError) as exc_info:
            StageCreate(name="Test Stage")

        assert "stage_order" in str(exc_info.value)


class TestStage:
    """Tests for Stage response model."""

    def test_stage_response(self):
        """Test stage response model."""
        from src.services.production.ledger_models import Stage

        now = datetime.now()
        stage = Stage(
            id=1,
            ledger_id=10,
            name="Component Manufacturing",
            stage_order=1,
            status="pending",
            material_cost=0,
            job_cost=0,
            completed_at=None,
            created_at=now,
            updated_at=now
        )

        assert stage.id == 1
        assert stage.ledger_id == 10
        assert stage.name == "Component Manufacturing"
        assert stage.stage_order == 1
        assert stage.status == "pending"


class TestStageUpdate:
    """Tests for StageUpdate model."""

    def test_stage_update_name(self):
        """Test updating stage name."""
        from src.services.production.ledger_models import StageUpdate

        update = StageUpdate(name="New Stage Name")

        assert update.name == "New Stage Name"
        assert update.status is None

    def test_stage_update_status(self):
        """Test updating stage status."""
        from src.services.production.ledger_models import StageUpdate

        update = StageUpdate(status="in_progress")

        assert update.status == "in_progress"


class TestJobCreate:
    """Tests for JobCreate model."""

    def test_minimal_job_create(self):
        """Test creating job with minimal fields."""
        from src.services.production.ledger_models import JobCreate

        job = JobCreate(
            type_id=34,
            quantity=1000,
            runs=10
        )

        assert job.type_id == 34
        assert job.quantity == 1000
        assert job.runs == 10
        assert job.me_level == 0
        assert job.te_level == 0

    def test_full_job_create(self):
        """Test creating job with all fields."""
        from src.services.production.ledger_models import JobCreate

        job = JobCreate(
            type_id=19720,
            quantity=1,
            runs=1,
            me_level=10,
            te_level=20
        )

        assert job.type_id == 19720
        assert job.quantity == 1
        assert job.runs == 1
        assert job.me_level == 10
        assert job.te_level == 20

    def test_job_requires_type_id(self):
        """Test that type_id is required."""
        from src.services.production.ledger_models import JobCreate

        with pytest.raises(ValidationError) as exc_info:
            JobCreate(quantity=1000, runs=10)

        assert "type_id" in str(exc_info.value)


class TestJob:
    """Tests for Job response model."""

    def test_job_response(self):
        """Test job response model."""
        from src.services.production.ledger_models import Job

        now = datetime.now()
        job = Job(
            id=1,
            ledger_id=10,
            stage_id=5,
            type_id=19720,
            type_name="Revelation",
            blueprint_type_id=19721,
            quantity=1,
            runs=1,
            me_level=10,
            te_level=20,
            facility_id=2,
            material_cost=5000000000,
            job_cost=100000000,
            production_time=86400,
            status="pending",
            esi_job_id=None,
            started_at=None,
            completed_at=None,
            created_at=now
        )

        assert job.id == 1
        assert job.type_name == "Revelation"
        assert job.material_cost == 5000000000
        assert job.production_time == 86400


class TestJobUpdate:
    """Tests for JobUpdate model."""

    def test_job_update_status(self):
        """Test updating job status."""
        from src.services.production.ledger_models import JobUpdate

        update = JobUpdate(status="in_progress")

        assert update.status == "in_progress"

    def test_job_update_esi_job_id(self):
        """Test updating ESI job ID."""
        from src.services.production.ledger_models import JobUpdate

        update = JobUpdate(esi_job_id=123456789)

        assert update.esi_job_id == 123456789


class TestMaterial:
    """Tests for Material model."""

    def test_material_creation(self):
        """Test creating material model."""
        from src.services.production.ledger_models import Material

        material = Material(
            id=1,
            ledger_id=10,
            type_id=34,
            type_name="Tritanium",
            total_needed=1000000,
            total_acquired=500000,
            estimated_cost=500000000,
            source="buy"
        )

        assert material.type_id == 34
        assert material.type_name == "Tritanium"
        assert material.total_needed == 1000000
        assert material.total_acquired == 500000
        assert material.estimated_cost == 500000000
        assert material.source == "buy"

    def test_material_with_minimal_fields(self):
        """Test material with nullable fields."""
        from src.services.production.ledger_models import Material

        material = Material(
            id=1,
            ledger_id=10,
            type_id=34,
            type_name=None,
            total_needed=1000,
            total_acquired=0,
            estimated_cost=0,
            source="build"
        )

        assert material.type_name is None
        assert material.total_acquired == 0


class TestMaterialUpsert:
    """Tests for MaterialUpsert model."""

    def test_material_upsert(self):
        """Test material upsert model."""
        from src.services.production.ledger_models import MaterialUpsert

        upsert = MaterialUpsert(
            type_id=34,
            type_name="Tritanium",
            total_needed=1000000,
            estimated_cost=500000000,
            source="buy"
        )

        assert upsert.type_id == 34
        assert upsert.total_needed == 1000000
        assert upsert.total_acquired == 0  # default


class TestLedgerWithDetails:
    """Tests for LedgerWithDetails model."""

    def test_ledger_with_empty_details(self):
        """Test ledger with no stages, jobs, or materials."""
        from src.services.production.ledger_models import Ledger, LedgerWithDetails

        now = datetime.now()
        ledger = Ledger(
            id=1,
            character_id=123456,
            name="Test Project",
            target_type_id=None,
            target_type_name=None,
            target_quantity=1,
            status="planning",
            tax_profile_id=None,
            facility_id=None,
            total_material_cost=0,
            total_job_cost=0,
            total_cost=0,
            expected_revenue=0,
            expected_profit=0,
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now
        )

        detailed = LedgerWithDetails(
            **ledger.model_dump(),
            stages=[],
            materials=[]
        )

        assert detailed.id == 1
        assert detailed.stages == []
        assert detailed.materials == []

    def test_ledger_with_stages_and_materials(self):
        """Test ledger with stages and materials populated."""
        from src.services.production.ledger_models import (
            Ledger, LedgerWithDetails, StageWithJobs, Material
        )

        now = datetime.now()
        ledger = Ledger(
            id=1,
            character_id=123456,
            name="Test Project",
            target_type_id=19720,
            target_type_name="Revelation",
            target_quantity=1,
            status="active",
            tax_profile_id=1,
            facility_id=2,
            total_material_cost=5000000000,
            total_job_cost=100000000,
            total_cost=5100000000,
            expected_revenue=6000000000,
            expected_profit=900000000,
            started_at=now,
            completed_at=None,
            created_at=now,
            updated_at=now
        )

        stage = StageWithJobs(
            id=1,
            ledger_id=1,
            name="Components",
            stage_order=1,
            status="pending",
            material_cost=0,
            job_cost=0,
            completed_at=None,
            created_at=now,
            updated_at=now,
            jobs=[]
        )

        material = Material(
            id=1,
            ledger_id=1,
            type_id=34,
            type_name="Tritanium",
            total_needed=1000000,
            total_acquired=0,
            estimated_cost=500000000,
            source="buy"
        )

        detailed = LedgerWithDetails(
            **ledger.model_dump(),
            stages=[stage],
            materials=[material]
        )

        assert detailed.id == 1
        assert len(detailed.stages) == 1
        assert detailed.stages[0].name == "Components"
        assert len(detailed.materials) == 1
        assert detailed.materials[0].type_name == "Tritanium"


class TestStageWithJobs:
    """Tests for StageWithJobs model."""

    def test_stage_with_jobs(self):
        """Test stage with jobs populated."""
        from src.services.production.ledger_models import Stage, StageWithJobs, Job

        now = datetime.now()
        job = Job(
            id=1,
            ledger_id=10,
            stage_id=1,
            type_id=19720,
            type_name="Revelation",
            blueprint_type_id=19721,
            quantity=1,
            runs=1,
            me_level=10,
            te_level=20,
            facility_id=2,
            material_cost=5000000000,
            job_cost=100000000,
            production_time=86400,
            status="pending",
            esi_job_id=None,
            started_at=None,
            completed_at=None,
            created_at=now
        )

        stage = StageWithJobs(
            id=1,
            ledger_id=10,
            name="Final Assembly",
            stage_order=3,
            status="pending",
            material_cost=0,
            job_cost=0,
            completed_at=None,
            created_at=now,
            updated_at=now,
            jobs=[job]
        )

        assert stage.id == 1
        assert len(stage.jobs) == 1
        assert stage.jobs[0].type_name == "Revelation"
