"""Test character sync staggering logic."""
import pytest


def test_stagger_delay_first_char():
    from jobs.character_sync import calculate_stagger_delay
    assert calculate_stagger_delay(0, 100) == 0


def test_stagger_delay_distributes_evenly():
    from jobs.character_sync import calculate_stagger_delay
    delay_50 = calculate_stagger_delay(50, 100, window_seconds=1500)
    assert 700 < delay_50 < 800  # ~750s = 50 * 15s


def test_stagger_delay_has_jitter():
    from jobs.character_sync import calculate_stagger_delay
    delays = {calculate_stagger_delay(10, 100) for _ in range(30)}
    assert len(delays) > 1  # Jitter makes delays vary


def test_stagger_delay_within_window():
    from jobs.character_sync import calculate_stagger_delay
    for _ in range(100):
        d = calculate_stagger_delay(99, 100, window_seconds=1500)
        assert d <= 1500


def test_stagger_delay_single_char():
    from jobs.character_sync import calculate_stagger_delay
    assert calculate_stagger_delay(0, 1) == 0


def test_stagger_delay_few_chars_no_delay():
    """With <= STAGGER_THRESHOLD chars, skip staggering."""
    from jobs.character_sync import calculate_stagger_delay
    assert calculate_stagger_delay(2, 4) == 0
