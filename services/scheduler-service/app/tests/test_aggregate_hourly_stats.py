"""Tests for market_history_sync.calculate_metrics and job model validation.

Tests:
- market_history_sync: calculate_metrics (pure function, no DB)
- models/job.py: JobDefinition, JobStatus, JobTriggerType construction/validation
"""

import pytest
from app.jobs.market_history_sync import calculate_metrics
from app.models.job import JobDefinition, JobStatus, JobTriggerType, JobRun, JobInfo


# =============================================================================
# calculate_metrics (market history)
# =============================================================================

class TestCalculateMetrics:
    """Test trading metrics calculation from market history data."""

    def _make_history(self, days=30, avg_price=100.0, volume=500, variance=5.0):
        """Helper: generate synthetic history data."""
        import random
        random.seed(42)
        return [
            {
                'date': f"2026-01-{i+1:02d}",
                'average': avg_price + random.uniform(-variance, variance),
                'volume': volume + random.randint(-50, 50),
                'lowest': avg_price - 10,
                'highest': avg_price + 10,
                'order_count': 100,
            }
            for i in range(days)
        ]

    def test_returns_none_for_empty_history(self):
        assert calculate_metrics([]) is None

    def test_returns_none_for_short_history(self):
        """Less than 7 days should return None."""
        history = self._make_history(days=5)
        assert calculate_metrics(history) is None

    def test_returns_dict_for_valid_history(self):
        history = self._make_history(days=30)
        result = calculate_metrics(history)
        assert result is not None
        assert 'avg_daily_volume' in result
        assert 'price_volatility' in result
        assert 'trend_7d' in result
        assert 'days_to_sell_100' in result
        assert 'risk_score' in result

    def test_avg_daily_volume_reasonable(self):
        history = self._make_history(days=30, volume=1000)
        result = calculate_metrics(history)
        # Volume averages around 1000 with +-50 noise
        assert 900 <= result['avg_daily_volume'] <= 1100

    def test_low_volatility(self):
        """Stable prices should have low volatility."""
        history = self._make_history(days=30, avg_price=100, variance=0.01)
        result = calculate_metrics(history)
        assert result['price_volatility'] < 1.0

    def test_high_volume_low_risk(self):
        """High-volume items should have lower risk score."""
        history = self._make_history(days=30, volume=5000, variance=1.0)
        result = calculate_metrics(history)
        assert result['risk_score'] < 50

    def test_low_volume_higher_risk(self):
        """Low-volume items should have higher risk."""
        history = self._make_history(days=30, volume=20, variance=1.0)
        result = calculate_metrics(history)
        assert result['risk_score'] >= 15  # At least volume_score component

    def test_risk_score_bounded(self):
        """Risk score must be between 0 and 100."""
        for vol in [10, 100, 1000, 10000]:
            history = self._make_history(days=30, volume=vol)
            result = calculate_metrics(history)
            assert 0 <= result['risk_score'] <= 100

    def test_days_to_sell_calculated(self):
        history = self._make_history(days=30, volume=200)
        result = calculate_metrics(history)
        # 100 units / ~200 per day = ~0.5 days
        assert result['days_to_sell_100'] is not None
        assert 0.3 <= result['days_to_sell_100'] <= 1.5

    def test_trend_7d_stable_market(self):
        """Near-constant prices should have near-zero trend."""
        history = self._make_history(days=30, avg_price=100, variance=0.001)
        result = calculate_metrics(history)
        assert abs(result['trend_7d']) < 1.0

    def test_zero_price_entries_skipped(self):
        """Entries with average=0 should be filtered from price calculations."""
        history = self._make_history(days=15)
        history[0]['average'] = 0
        history[1]['average'] = 0
        result = calculate_metrics(history)
        assert result is not None


# =============================================================================
# JobDefinition model
# =============================================================================

class TestJobDefinitionModel:
    """Test Pydantic model validation for JobDefinition."""

    def test_minimal_valid_definition(self):
        job = JobDefinition(
            id="test_job",
            name="Test Job",
            func="app.jobs.executors.run_test",
        )
        assert job.id == "test_job"
        assert job.enabled is True
        assert job.max_instances == 1
        assert job.tags == []

    def test_disabled_job(self):
        job = JobDefinition(
            id="disabled_job",
            name="Disabled",
            func="app.jobs.executors.run_disabled",
            enabled=False,
        )
        assert job.enabled is False

    def test_cron_trigger_with_args(self):
        job = JobDefinition(
            id="cron_job",
            name="Cron Job",
            func="app.jobs.executors.run_cron",
            trigger_type=JobTriggerType.CRON,
            trigger_args={"minute": "*/5", "hour": "0-6"},
        )
        assert job.trigger_type == JobTriggerType.CRON
        assert job.trigger_args["minute"] == "*/5"

    def test_tags_preserved(self):
        job = JobDefinition(
            id="tagged_job",
            name="Tagged",
            func="app.jobs.executors.run_tagged",
            tags=["market", "high-frequency", "critical"],
        )
        assert "market" in job.tags
        assert len(job.tags) == 3


class TestJobStatusEnum:
    """Test JobStatus enum values."""

    @pytest.mark.parametrize("status,value", [
        (JobStatus.PENDING, "pending"),
        (JobStatus.RUNNING, "running"),
        (JobStatus.SUCCESS, "success"),
        (JobStatus.FAILED, "failed"),
        (JobStatus.SKIPPED, "skipped"),
    ])
    def test_status_values(self, status, value):
        assert status.value == value

    def test_status_count(self):
        """Should have exactly 5 statuses."""
        assert len(JobStatus) == 5


class TestJobTriggerTypeEnum:
    """Test JobTriggerType enum values."""

    @pytest.mark.parametrize("trigger,value", [
        (JobTriggerType.CRON, "cron"),
        (JobTriggerType.INTERVAL, "interval"),
        (JobTriggerType.DATE, "date"),
    ])
    def test_trigger_values(self, trigger, value):
        assert trigger.value == value
