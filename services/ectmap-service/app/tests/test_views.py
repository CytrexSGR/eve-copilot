"""Tests for ectmap-service models, config, views, and snapshot logic."""

import json
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.config import MAPS
from app.models import (
    MapInfo,
    SnapshotRequest,
    SnapshotResponse,
    ViewCreate,
    ViewResponse,
)
from app.views import _row_to_response


# ============================================================
# MAPS config constants
# ============================================================

class TestMapsConfig:
    """Tests for MAPS configuration dictionary."""

    def test_three_map_types_defined(self):
        assert set(MAPS.keys()) == {"ectmap", "sovmap", "capitalmap"}

    @pytest.mark.parametrize("map_type", ["ectmap", "sovmap", "capitalmap"])
    def test_map_has_required_keys(self, map_type):
        config = MAPS[map_type]
        assert "url" in config
        assert "port" in config
        assert "params" in config

    @pytest.mark.parametrize("map_type", ["ectmap", "sovmap", "capitalmap"])
    def test_params_is_list_of_strings(self, map_type):
        params = MAPS[map_type]["params"]
        assert isinstance(params, list)
        assert all(isinstance(p, str) for p in params)

    def test_ectmap_params_include_battles(self):
        assert "showBattles" in MAPS["ectmap"]["params"]

    def test_sovmap_params_include_jammers(self):
        assert "showJammers" in MAPS["sovmap"]["params"]

    def test_capitalmap_params_include_timers(self):
        assert "showTimers" in MAPS["capitalmap"]["params"]

    def test_all_maps_have_region_param(self):
        for name, config in MAPS.items():
            assert "region" in config["params"], f"{name} missing region param"

    @pytest.mark.parametrize("map_type,port", [
        ("ectmap", 3001),
        ("sovmap", 3004),
        ("capitalmap", 3005),
    ])
    def test_ports(self, map_type, port):
        assert MAPS[map_type]["port"] == port


# ============================================================
# Pydantic Models - SnapshotRequest
# ============================================================

class TestSnapshotRequest:
    """Tests for SnapshotRequest Pydantic model validation."""

    def test_defaults(self):
        req = SnapshotRequest(map_type="ectmap")
        assert req.width == 1920
        assert req.height == 1080
        assert req.wait_ms == 3000
        assert req.region is None
        assert req.params == {}

    def test_custom_values(self):
        req = SnapshotRequest(
            map_type="sovmap",
            region="Detorid",
            width=2560,
            height=1440,
            wait_ms=5000,
            params={"colorMode": "sov"},
        )
        assert req.map_type == "sovmap"
        assert req.region == "Detorid"
        assert req.width == 2560

    def test_width_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            SnapshotRequest(map_type="ectmap", width=799)

    def test_width_above_maximum_rejected(self):
        with pytest.raises(ValidationError):
            SnapshotRequest(map_type="ectmap", width=3841)

    def test_height_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            SnapshotRequest(map_type="ectmap", height=599)

    def test_height_above_maximum_rejected(self):
        with pytest.raises(ValidationError):
            SnapshotRequest(map_type="ectmap", height=2161)

    def test_wait_ms_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            SnapshotRequest(map_type="ectmap", wait_ms=999)

    def test_wait_ms_above_maximum_rejected(self):
        with pytest.raises(ValidationError):
            SnapshotRequest(map_type="ectmap", wait_ms=10001)

    @pytest.mark.parametrize("w,h", [
        (800, 600),    # minimum
        (3840, 2160),  # maximum
        (1920, 1080),  # default
    ])
    def test_boundary_values_accepted(self, w, h):
        req = SnapshotRequest(map_type="ectmap", width=w, height=h)
        assert req.width == w
        assert req.height == h


# ============================================================
# Pydantic Models - ViewCreate
# ============================================================

class TestViewCreate:
    """Tests for ViewCreate Pydantic model."""

    def test_minimal_creation(self):
        view = ViewCreate(name="Test View", map_type="ectmap")
        assert view.name == "Test View"
        assert view.description is None
        assert view.auto_snapshot is False
        assert view.snapshot_schedule is None
        assert view.width == 1920
        assert view.height == 1080

    def test_full_creation(self):
        view = ViewCreate(
            name="Sov Watch",
            description="Monitor sovereignty changes",
            map_type="sovmap",
            region="Tribute",
            width=2560,
            height=1440,
            params={"showJammers": True},
            auto_snapshot=True,
            snapshot_schedule="0 */6 * * *",
        )
        assert view.auto_snapshot is True
        assert view.params == {"showJammers": True}

    def test_map_type_required(self):
        with pytest.raises(ValidationError):
            ViewCreate(name="No Map Type")


# ============================================================
# Pydantic Models - ViewResponse
# ============================================================

class TestViewResponse:
    """Tests for ViewResponse Pydantic model."""

    def test_full_response(self):
        resp = ViewResponse(
            id=1,
            name="Test",
            description=None,
            map_type="ectmap",
            region=None,
            width=1920,
            height=1080,
            params={},
            auto_snapshot=False,
            snapshot_schedule=None,
            last_snapshot_at=None,
            last_snapshot_id=None,
            created_at="2026-01-15T08:30:00",
        )
        assert resp.id == 1
        assert resp.last_snapshot_at is None

    def test_with_snapshot(self):
        resp = ViewResponse(
            id=2,
            name="Active",
            description="Has snapshot",
            map_type="sovmap",
            region="Detorid",
            width=1920,
            height=1080,
            params={"colorMode": "sov"},
            auto_snapshot=True,
            snapshot_schedule="0 */6 * * *",
            last_snapshot_at="2026-02-10T12:00:00",
            last_snapshot_id="sovmap-20260210-abc",
            created_at="2026-01-15T08:30:00",
        )
        assert resp.last_snapshot_id == "sovmap-20260210-abc"


# ============================================================
# Pydantic Models - SnapshotResponse
# ============================================================

class TestSnapshotResponse:
    """Tests for SnapshotResponse Pydantic model."""

    def test_creation(self):
        resp = SnapshotResponse(
            snapshot_id="ectmap-20260210-120000-abc12345",
            filename="ectmap-20260210-120000-abc12345.png",
            url="/snapshots/ectmap-20260210-120000-abc12345.png",
            map_type="ectmap",
            created_at="2026-02-10T12:00:00",
            params={"snapshot": "true"},
        )
        assert resp.map_type == "ectmap"
        assert resp.url.endswith(".png")


# ============================================================
# Pydantic Models - MapInfo
# ============================================================

class TestMapInfo:
    """Tests for MapInfo Pydantic model."""

    def test_creation(self):
        info = MapInfo(
            name="ectmap",
            url="http://localhost:3001/ectmap",
            port=3001,
            params=["colorMode", "showBattles"],
            status="online",
        )
        assert info.status == "online"

    def test_default_status(self):
        info = MapInfo(name="test", url="http://x", port=9999, params=[])
        assert info.status == "unknown"


# ============================================================
# _row_to_response conversion
# ============================================================

class TestRowToResponse:
    """Tests for DB row dict to ViewResponse conversion."""

    def test_basic_conversion(self, sample_view_row):
        resp = _row_to_response(sample_view_row)
        assert isinstance(resp, ViewResponse)
        assert resp.id == 1
        assert resp.name == "Fraternity Sov Map"
        assert resp.map_type == "sovmap"
        assert resp.region == "Detorid"
        assert resp.width == 1920
        assert resp.auto_snapshot is True

    def test_datetime_to_isoformat(self, sample_view_row):
        resp = _row_to_response(sample_view_row)
        assert resp.created_at == "2026-01-15T08:30:00"
        assert resp.last_snapshot_at == "2026-02-10T12:00:00"

    def test_none_last_snapshot_at(self, sample_view_row):
        sample_view_row["last_snapshot_at"] = None
        sample_view_row["last_snapshot_id"] = None
        resp = _row_to_response(sample_view_row)
        assert resp.last_snapshot_at is None
        assert resp.last_snapshot_id is None

    def test_params_dict_passthrough(self, sample_view_row):
        """When params is already a dict, it should pass through unchanged."""
        resp = _row_to_response(sample_view_row)
        assert resp.params == {"colorMode": "sov", "showJammers": True}

    def test_params_json_string_parsed(self, sample_view_row):
        """When params is a JSON string (from some DB drivers), it should be parsed."""
        sample_view_row["params"] = json.dumps({"colorMode": "security"})
        resp = _row_to_response(sample_view_row)
        assert resp.params == {"colorMode": "security"}

    def test_description_nullable(self, sample_view_row):
        sample_view_row["description"] = None
        resp = _row_to_response(sample_view_row)
        assert resp.description is None

    def test_snapshot_schedule_nullable(self, sample_view_row):
        sample_view_row["snapshot_schedule"] = None
        resp = _row_to_response(sample_view_row)
        assert resp.snapshot_schedule is None
