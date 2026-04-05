"""Tests for job definitions — validate structure, uniqueness, and consistency."""

import pytest
from app.jobs.definitions import JOB_DEFINITIONS, get_job_definitions, get_job_by_id
from app.models.job import JobTriggerType


class TestJobDefinitionsStructure:
    """Validate the structure and constraints of JOB_DEFINITIONS."""

    def test_all_job_ids_unique(self):
        """Every job must have a unique ID."""
        ids = [j.id for j in JOB_DEFINITIONS]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {[x for x in ids if ids.count(x) > 1]}"

    def test_all_job_names_non_empty(self):
        """Every job must have a non-empty name."""
        for job in JOB_DEFINITIONS:
            assert job.name, f"Job {job.id} has empty name"

    def test_all_jobs_have_func_path(self):
        """Every job must reference a function path."""
        for job in JOB_DEFINITIONS:
            assert job.func, f"Job {job.id} has no func"
            assert "." in job.func, f"Job {job.id} func must be a dotted path: {job.func}"

    def test_all_trigger_types_valid(self):
        """Every job trigger_type must be a valid JobTriggerType."""
        for job in JOB_DEFINITIONS:
            assert isinstance(job.trigger_type, JobTriggerType), (
                f"Job {job.id} has invalid trigger_type: {job.trigger_type}"
            )

    def test_cron_jobs_have_trigger_args(self):
        """Every CRON job must specify at least one trigger arg (minute, hour, etc.)."""
        for job in JOB_DEFINITIONS:
            if job.trigger_type == JobTriggerType.CRON:
                assert job.trigger_args, f"CRON job {job.id} has no trigger_args"

    def test_all_tags_are_strings(self):
        """Every tag must be a non-empty string."""
        for job in JOB_DEFINITIONS:
            for tag in job.tags:
                assert isinstance(tag, str) and tag, (
                    f"Job {job.id} has invalid tag: {tag!r}"
                )

    def test_max_instances_positive(self):
        """max_instances must be >= 1."""
        for job in JOB_DEFINITIONS:
            assert job.max_instances >= 1, (
                f"Job {job.id} has max_instances={job.max_instances}"
            )

    def test_misfire_grace_time_positive(self):
        """misfire_grace_time must be > 0."""
        for job in JOB_DEFINITIONS:
            assert job.misfire_grace_time > 0, (
                f"Job {job.id} has misfire_grace_time={job.misfire_grace_time}"
            )

    def test_minimum_job_count(self):
        """There should be at least 30 jobs defined (sanity check)."""
        assert len(JOB_DEFINITIONS) >= 30, (
            f"Expected 30+ jobs, got {len(JOB_DEFINITIONS)}"
        )


class TestGetJobDefinitions:
    """Tests for helper functions that query job definitions."""

    def test_get_job_definitions_returns_list(self):
        """get_job_definitions() should return the full list."""
        result = get_job_definitions()
        assert result is JOB_DEFINITIONS

    def test_get_job_by_id_found(self):
        """get_job_by_id() returns the correct job."""
        job = get_job_by_id("token_refresh")
        assert job is not None
        assert job.id == "token_refresh"
        assert job.name == "OAuth Token Refresh"

    def test_get_job_by_id_not_found(self):
        """get_job_by_id() returns None for unknown IDs."""
        assert get_job_by_id("nonexistent_job_xyz") is None

    @pytest.mark.parametrize("job_id", [
        "token_refresh",
        "aggregate_hourly_stats",
        "aggregate_corp_hourly_stats",
        "batch_calculator",
        "regional_prices",
        "character_sync",
        "alliance_wars",
        "killmail_fetcher",
        "pilot_skill_estimates",
        "payment_poll",
        "subscription_expiry",
    ])
    def test_known_jobs_exist(self, job_id):
        """Critical jobs must exist in definitions."""
        job = get_job_by_id(job_id)
        assert job is not None, f"Job {job_id!r} missing from definitions"


class TestJobFuncPaths:
    """Validate that job func paths follow the expected pattern."""

    def test_all_func_paths_start_with_app(self):
        """All func paths should start with 'app.jobs.executors'."""
        for job in JOB_DEFINITIONS:
            assert job.func.startswith("app.jobs.executors."), (
                f"Job {job.id} func doesn't start with 'app.jobs.executors.': {job.func}"
            )

    def test_all_func_paths_start_with_run(self):
        """All executor function names should start with 'run_'."""
        for job in JOB_DEFINITIONS:
            func_name = job.func.rsplit(".", 1)[-1]
            assert func_name.startswith("run_"), (
                f"Job {job.id} func name doesn't start with 'run_': {func_name}"
            )
