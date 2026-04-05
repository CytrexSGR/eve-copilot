"""View CRUD operations."""
import json
from typing import Optional, List
from .database import db_cursor
from .models import ViewCreate, ViewResponse


def create_view(view: ViewCreate) -> ViewResponse:
    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO map_views (name, description, map_type, region, width, height, params, auto_snapshot, snapshot_schedule)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (view.name, view.description, view.map_type, view.region, view.width, view.height,
              json.dumps(view.params), view.auto_snapshot, view.snapshot_schedule))
        return _row_to_response(cur.fetchone())


def get_view(view_id: int) -> Optional[ViewResponse]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM map_views WHERE id = %s", (view_id,))
        row = cur.fetchone()
        return _row_to_response(row) if row else None


def list_views(map_type: Optional[str] = None) -> List[ViewResponse]:
    with db_cursor() as cur:
        if map_type:
            cur.execute("SELECT * FROM map_views WHERE map_type = %s ORDER BY name", (map_type,))
        else:
            cur.execute("SELECT * FROM map_views ORDER BY map_type, name")
        return [_row_to_response(row) for row in cur.fetchall()]


def update_view(view_id: int, view: ViewCreate) -> Optional[ViewResponse]:
    with db_cursor() as cur:
        cur.execute("""
            UPDATE map_views SET name=%s, description=%s, map_type=%s, region=%s,
            width=%s, height=%s, params=%s, auto_snapshot=%s, snapshot_schedule=%s, updated_at=NOW()
            WHERE id = %s RETURNING *
        """, (view.name, view.description, view.map_type, view.region, view.width, view.height,
              json.dumps(view.params), view.auto_snapshot, view.snapshot_schedule, view_id))
        row = cur.fetchone()
        return _row_to_response(row) if row else None


def delete_view(view_id: int) -> bool:
    with db_cursor() as cur:
        cur.execute("DELETE FROM map_views WHERE id = %s", (view_id,))
        return cur.rowcount > 0


def update_view_snapshot(view_id: int, snapshot_id: str):
    with db_cursor() as cur:
        cur.execute("UPDATE map_views SET last_snapshot_at=NOW(), last_snapshot_id=%s WHERE id=%s",
                    (snapshot_id, view_id))


def _row_to_response(row: dict) -> ViewResponse:
    return ViewResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        map_type=row["map_type"],
        region=row["region"],
        width=row["width"],
        height=row["height"],
        params=row["params"] if isinstance(row["params"], dict) else json.loads(row["params"]),
        auto_snapshot=row["auto_snapshot"],
        snapshot_schedule=row["snapshot_schedule"],
        last_snapshot_at=row["last_snapshot_at"].isoformat() if row["last_snapshot_at"] else None,
        last_snapshot_id=row["last_snapshot_id"],
        created_at=row["created_at"].isoformat(),
    )
