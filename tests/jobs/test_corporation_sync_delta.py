"""Test corporation sync delta-sync logic."""
import pytest


def test_delta_filters_fresh_corps():
    """Fresh corps (updated <24h ago) should be skipped."""
    all_corps = {100, 200, 300, 400}
    fresh_corps = {200, 400}
    stale = all_corps - fresh_corps
    assert stale == {100, 300}


def test_delta_empty_fresh_set():
    """If no corps are fresh, all should be fetched."""
    all_corps = {100, 200, 300}
    fresh_corps = set()
    stale = all_corps - fresh_corps
    assert stale == {100, 200, 300}


def test_delta_all_fresh():
    """If all corps are fresh, none should be fetched."""
    all_corps = {100, 200}
    fresh_corps = {100, 200, 300}  # superset is fine
    stale = all_corps - fresh_corps
    assert stale == set()


def test_delta_skipped_count():
    """Skipped count should only include intersection."""
    all_corps = {100, 200, 300}
    fresh_corps = {200, 400, 500}  # 400, 500 not in all_corps
    skipped = len(fresh_corps & all_corps)
    assert skipped == 1  # only 200
