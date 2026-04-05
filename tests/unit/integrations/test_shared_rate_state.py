"""Test shared ESI rate limit state via Redis."""
import pytest
from unittest.mock import MagicMock


class TestSharedRateState:
    @pytest.fixture
    def mock_redis(self):
        r = MagicMock()
        r.get.return_value = None
        return r

    @pytest.fixture
    def rate_state(self, mock_redis):
        from src.integrations.esi.shared_rate_state import SharedRateState
        state = SharedRateState()
        state._redis = mock_redis
        return state

    def test_update_from_headers_stores_in_redis(self, rate_state, mock_redis):
        rate_state.update_from_headers({
            "X-ESI-Error-Limit-Remain": "75",
            "X-ESI-Error-Limit-Reset": "45"
        })
        mock_redis.set.assert_any_call("esi:error_limit_remain", "75", ex=120)

    def test_get_error_remaining_reads_redis(self, rate_state, mock_redis):
        mock_redis.get.return_value = "42"
        assert rate_state.get_error_remaining() == 42

    def test_get_error_remaining_fallback_local(self, rate_state):
        rate_state._redis = None
        rate_state._local_error_remain = 88
        assert rate_state.get_error_remaining() == 88

    def test_is_globally_banned(self, rate_state, mock_redis):
        mock_redis.get.return_value = "1"
        assert rate_state.is_globally_banned() is True

    def test_not_globally_banned(self, rate_state, mock_redis):
        mock_redis.get.return_value = None
        assert rate_state.is_globally_banned() is False

    def test_set_global_ban(self, rate_state, mock_redis):
        rate_state.set_global_ban(duration_seconds=120)
        mock_redis.setex.assert_called_once_with("esi:global_ban", 120, "1")

    def test_should_hard_stop_when_critical(self, rate_state, mock_redis):
        mock_redis.get.return_value = "5"
        assert rate_state.should_hard_stop() is True

    def test_should_not_hard_stop_when_safe(self, rate_state, mock_redis):
        mock_redis.get.return_value = "50"
        assert rate_state.should_hard_stop() is False

    def test_should_throttle_at_threshold(self, rate_state, mock_redis):
        mock_redis.get.return_value = "25"
        assert rate_state.should_throttle() is True

    def test_should_not_throttle_above_threshold(self, rate_state, mock_redis):
        mock_redis.get.return_value = "60"
        assert rate_state.should_throttle() is False
