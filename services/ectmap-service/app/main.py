"""ECTMap Service API."""
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from .config import MAPS, SNAPSHOT_DIR
from .models import (
    MapInfo, SnapshotRequest, SnapshotResponse, ViewCreate, ViewResponse,
    AtomicSnapshotRequest, AtomicSnapshotResponse,
)
from .snapshot import (
    generate_snapshot, generate_atomic_snapshot,
    list_snapshots, get_snapshot_data, delete_snapshot,
)
from . import views

app = FastAPI(title="ECTMap Service", version="2.0.0")

try:
    from eve_shared.middleware.exception_handler import register_exception_handlers
    register_exception_handlers(app)
except ImportError:
    pass


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ectmap-service", "version": "2.0.0"}


# --- Maps ---

@app.get("/api/maps", response_model=list[MapInfo])
async def get_maps():
    result = []
    async with httpx.AsyncClient(timeout=2.0) as client:
        for name, config in MAPS.items():
            status = "unknown"
            try:
                resp = await client.get(config["url"])
                status = "online" if resp.status_code == 200 else "error"
            except Exception:
                status = "offline"
            result.append(MapInfo(name=name, url=config["url"], port=config["port"],
                                   params=config["params"], status=status))
    return result


# --- Snapshots ---

@app.post("/api/snapshots", response_model=SnapshotResponse)
async def create_snapshot(request: SnapshotRequest):
    if request.map_type not in MAPS:
        raise HTTPException(400, f"Unknown map: {request.map_type}")
    try:
        result = await generate_snapshot(
            map_type=request.map_type, region=request.region,
            width=request.width, height=request.height,
            wait_ms=request.wait_ms, params=request.params,
        )
        return SnapshotResponse(**result)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/snapshots/atomic", response_model=AtomicSnapshotResponse)
async def create_atomic_snapshot(request: AtomicSnapshotRequest):
    """Generate a screenshot + API data snapshot atomically."""
    if request.map_type not in MAPS:
        raise HTTPException(400, f"Unknown map: {request.map_type}")
    try:
        result = await generate_atomic_snapshot(
            map_type=request.map_type,
            minutes=request.minutes,
            region=request.region,
            color_mode=request.color_mode,
            width=request.width,
            height=request.height,
            wait_ms=request.wait_ms,
            extra_params=request.extra_params,
        )
        return AtomicSnapshotResponse(**result)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/snapshots")
async def get_snapshots(limit: int = 50, map_type: str = None):
    snapshots = list_snapshots(limit)
    if map_type:
        snapshots = [s for s in snapshots if s["map_type"] == map_type]
    return {"snapshots": snapshots, "count": len(snapshots)}


@app.get("/api/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: str):
    filepath = Path(SNAPSHOT_DIR) / f"{snapshot_id}.png"
    if not filepath.exists():
        raise HTTPException(404, "Snapshot not found")
    return FileResponse(str(filepath), media_type="image/png")


@app.get("/api/snapshots/{snapshot_id}/data")
async def get_snapshot_data_endpoint(snapshot_id: str):
    """Get the API data associated with an atomic snapshot."""
    data = get_snapshot_data(snapshot_id)
    if data is None:
        raise HTTPException(404, "Snapshot data not found")
    return JSONResponse(content=data)


@app.delete("/api/snapshots/{snapshot_id}")
async def remove_snapshot(snapshot_id: str):
    if delete_snapshot(snapshot_id):
        return {"deleted": True}
    raise HTTPException(404, "Snapshot not found")


# --- Views ---

@app.get("/api/views", response_model=list[ViewResponse])
async def get_views(map_type: str = None):
    return views.list_views(map_type)


@app.post("/api/views", response_model=ViewResponse)
async def create_view(view: ViewCreate):
    if view.map_type not in MAPS:
        raise HTTPException(400, f"Unknown map: {view.map_type}")
    return views.create_view(view)


@app.get("/api/views/{view_id}", response_model=ViewResponse)
async def get_view(view_id: int):
    view = views.get_view(view_id)
    if not view:
        raise HTTPException(404, "View not found")
    return view


@app.put("/api/views/{view_id}", response_model=ViewResponse)
async def update_view(view_id: int, view: ViewCreate):
    result = views.update_view(view_id, view)
    if not result:
        raise HTTPException(404, "View not found")
    return result


@app.delete("/api/views/{view_id}")
async def remove_view(view_id: int):
    if views.delete_view(view_id):
        return {"deleted": True}
    raise HTTPException(404, "View not found")


@app.post("/api/views/{view_id}/render", response_model=SnapshotResponse)
async def render_view(view_id: int):
    view = views.get_view(view_id)
    if not view:
        raise HTTPException(404, "View not found")
    result = await generate_snapshot(
        map_type=view.map_type, region=view.region,
        width=view.width, height=view.height, params=view.params,
    )
    views.update_view_snapshot(view_id, result["snapshot_id"])
    return SnapshotResponse(**result)
