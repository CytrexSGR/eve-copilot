"""
Bookmarks Router - Bookmark management endpoints.
Migrated from monolith to market-service.
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bookmarks", tags=["Bookmarks"])


# --- Pydantic Models ---

class BookmarkCreate(BaseModel):
    """Schema for creating a bookmark."""
    type_id: int = Field(..., gt=0, description="EVE type ID (must be positive)")
    item_name: str = Field(..., min_length=1, max_length=255, description="Item name")
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list, description="List of tags")
    priority: int = Field(default=0, ge=0, description="Priority (non-negative)")


class Bookmark(BaseModel):
    """Bookmark entity."""
    id: int
    type_id: int
    item_name: str
    character_id: Optional[int]
    corporation_id: Optional[int]
    notes: Optional[str]
    tags: List[str]
    priority: int
    created_at: datetime
    updated_at: datetime


class BookmarkUpdate(BaseModel):
    """Schema for updating a bookmark."""
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = Field(None, ge=0, description="Priority (non-negative)")


class BookmarkListCreate(BaseModel):
    """Schema for creating a bookmark list."""
    name: str = Field(..., min_length=1, max_length=255, description="List name")
    description: Optional[str] = None
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    is_shared: bool = Field(default=False, description="Whether list is shared")


class BookmarkList(BaseModel):
    """Bookmark list entity."""
    id: int
    name: str
    description: Optional[str]
    character_id: Optional[int]
    corporation_id: Optional[int]
    is_shared: bool
    item_count: int = 0
    created_at: datetime
    updated_at: datetime


class BookmarkWithPosition(Bookmark):
    """Bookmark with position field for list items."""
    position: int = Field(..., description="Position in list")


# --- Helper Functions ---

def _row_to_bookmark(row: dict, columns: list = None) -> dict:
    """Convert a database row to bookmark dict.

    With RealDictCursor, row is already a dict, so columns param is ignored.
    """
    data = dict(row)  # Make a copy
    # Handle tags - may be stored as array or need conversion
    if 'tags' in data and data['tags'] is None:
        data['tags'] = []
    return data


# --- Endpoints ---

@router.post("")
@handle_endpoint_errors()
def create_bookmark(request: Request, bookmark_data: BookmarkCreate):
    """Create a new bookmark."""
    db = request.app.state.db
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO bookmarks
                (type_id, item_name, character_id, corporation_id, notes, tags, priority)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, type_id, item_name, character_id, corporation_id,
                      notes, tags, priority, created_at, updated_at
            """,
            (
                bookmark_data.type_id,
                bookmark_data.item_name,
                bookmark_data.character_id,
                bookmark_data.corporation_id,
                bookmark_data.notes,
                bookmark_data.tags,
                bookmark_data.priority
            )
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create bookmark")

        columns = ['id', 'type_id', 'item_name', 'character_id', 'corporation_id',
                   'notes', 'tags', 'priority', 'created_at', 'updated_at']
        return _row_to_bookmark(row, columns)


@router.get("")
@handle_endpoint_errors()
def get_bookmarks(
    request: Request,
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None),
    list_id: Optional[int] = Query(None)
):
    """Get bookmarks with optional filters."""
    db = request.app.state.db

    # If list_id is provided, get bookmarks from that list with position
    if list_id is not None:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT b.id, b.type_id, b.item_name, b.character_id, b.corporation_id,
                       b.notes, b.tags, b.priority, b.created_at, b.updated_at, bli.position
                FROM bookmarks b
                JOIN bookmark_list_items bli ON b.id = bli.bookmark_id
                WHERE bli.list_id = %s
                ORDER BY bli.position, b.created_at DESC
                """,
                (list_id,)
            )
            rows = cur.fetchall()

        columns = ['id', 'type_id', 'item_name', 'character_id', 'corporation_id',
                   'notes', 'tags', 'priority', 'created_at', 'updated_at', 'position']
        bookmarks = [_row_to_bookmark(row, columns) for row in rows]
        return {"bookmarks": bookmarks}

    # Otherwise, get all bookmarks with optional filters
    where_clauses = []
    params = []

    if character_id is not None:
        where_clauses.append("character_id = %s")
        params.append(character_id)
    if corporation_id is not None:
        where_clauses.append("corporation_id = %s")
        params.append(corporation_id)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    with db.cursor() as cur:
        cur.execute(
            f"""
            SELECT id, type_id, item_name, character_id, corporation_id,
                   notes, tags, priority, created_at, updated_at
            FROM bookmarks
            WHERE {where_sql}
            ORDER BY priority DESC, created_at DESC
            """,
            params
        )
        rows = cur.fetchall()

    columns = ['id', 'type_id', 'item_name', 'character_id', 'corporation_id',
               'notes', 'tags', 'priority', 'created_at', 'updated_at']
    bookmarks = [_row_to_bookmark(row, columns) for row in rows]
    return {"bookmarks": bookmarks}


@router.get("/check/{type_id}")
@handle_endpoint_errors()
def check_bookmark(
    request: Request,
    type_id: int,
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None)
):
    """Check if item is bookmarked."""
    db = request.app.state.db

    where_clauses = ["type_id = %s"]
    params = [type_id]

    if character_id is not None:
        where_clauses.append("character_id = %s")
        params.append(character_id)
    if corporation_id is not None:
        where_clauses.append("corporation_id = %s")
        params.append(corporation_id)

    with db.cursor() as cur:
        cur.execute(
            f"""
            SELECT id, type_id, item_name, character_id, corporation_id,
                   notes, tags, priority, created_at, updated_at
            FROM bookmarks
            WHERE {" AND ".join(where_clauses)}
            LIMIT 1
            """,
            params
        )
        row = cur.fetchone()

    if row:
        columns = ['id', 'type_id', 'item_name', 'character_id', 'corporation_id',
                   'notes', 'tags', 'priority', 'created_at', 'updated_at']
        bookmark = _row_to_bookmark(row, columns)
        return {"is_bookmarked": True, "bookmark": bookmark}
    else:
        return {"is_bookmarked": False, "bookmark": None}


@router.patch("/{bookmark_id}")
@handle_endpoint_errors()
def update_bookmark(
    request: Request,
    bookmark_id: int,
    bookmark_update: BookmarkUpdate
):
    """Update a bookmark."""
    db = request.app.state.db

    # Build update fields - only include non-None values
    updates = {}
    if bookmark_update.notes is not None:
        updates['notes'] = bookmark_update.notes
    if bookmark_update.tags is not None:
        updates['tags'] = bookmark_update.tags
    if bookmark_update.priority is not None:
        updates['priority'] = bookmark_update.priority

    if not updates:
        # No updates, just return current bookmark
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT id, type_id, item_name, character_id, corporation_id,
                       notes, tags, priority, created_at, updated_at
                FROM bookmarks WHERE id = %s
                """,
                (bookmark_id,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Bookmark not found")
            columns = ['id', 'type_id', 'item_name', 'character_id', 'corporation_id',
                       'notes', 'tags', 'priority', 'created_at', 'updated_at']
            return _row_to_bookmark(row, columns)

    set_clauses = ", ".join(f"{key} = %s" for key in updates.keys())
    query = f"""
        UPDATE bookmarks
        SET {set_clauses}, updated_at = NOW()
        WHERE id = %s
        RETURNING id, type_id, item_name, character_id, corporation_id,
                  notes, tags, priority, created_at, updated_at
    """

    with db.cursor() as cur:
        cur.execute(query, (*updates.values(), bookmark_id))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    columns = ['id', 'type_id', 'item_name', 'character_id', 'corporation_id',
               'notes', 'tags', 'priority', 'created_at', 'updated_at']
    return _row_to_bookmark(row, columns)


@router.delete("/{bookmark_id}")
@handle_endpoint_errors()
def delete_bookmark(request: Request, bookmark_id: int):
    """Delete a bookmark."""
    db = request.app.state.db

    with db.cursor() as cur:
        cur.execute("DELETE FROM bookmarks WHERE id = %s", (bookmark_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Bookmark not found")

    return {"status": "deleted"}


@router.post("/lists")
@handle_endpoint_errors()
def create_bookmark_list(request: Request, list_data: BookmarkListCreate):
    """Create a bookmark list."""
    db = request.app.state.db

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO bookmark_lists
                (name, description, character_id, corporation_id, is_shared)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, name, description, character_id, corporation_id,
                      is_shared, created_at, updated_at
            """,
            (
                list_data.name,
                list_data.description,
                list_data.character_id,
                list_data.corporation_id,
                list_data.is_shared
            )
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create bookmark list")

    return {
        "id": row['id'],
        "name": row['name'],
        "description": row['description'],
        "character_id": row['character_id'],
        "corporation_id": row['corporation_id'],
        "is_shared": row['is_shared'],
        "item_count": 0,
        "created_at": row['created_at'],
        "updated_at": row['updated_at']
    }


@router.get("/lists")
@handle_endpoint_errors()
def get_bookmark_lists(
    request: Request,
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None)
):
    """Get bookmark lists."""
    db = request.app.state.db

    where_clauses = []
    params = []

    if character_id is not None:
        where_clauses.append("(character_id = %s OR is_shared = TRUE)")
        params.append(character_id)
    if corporation_id is not None:
        where_clauses.append("corporation_id = %s")
        params.append(corporation_id)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    with db.cursor() as cur:
        cur.execute(
            f"""
            SELECT bl.id, bl.name, bl.description, bl.character_id, bl.corporation_id,
                   bl.is_shared, bl.created_at, bl.updated_at,
                   (SELECT COUNT(*) FROM bookmark_list_items WHERE list_id = bl.id) as item_count
            FROM bookmark_lists bl
            WHERE {where_sql}
            ORDER BY bl.name
            """,
            params
        )
        rows = cur.fetchall()

    lists = [
        {
            "id": row['id'],
            "name": row['name'],
            "description": row['description'],
            "character_id": row['character_id'],
            "corporation_id": row['corporation_id'],
            "is_shared": row['is_shared'],
            "created_at": row['created_at'],
            "updated_at": row['updated_at'],
            "item_count": row['item_count']
        }
        for row in rows
    ]
    return {"lists": lists}


@router.post("/lists/{list_id}/items/{bookmark_id}")
@handle_endpoint_errors()
def add_to_list(
    request: Request,
    list_id: int,
    bookmark_id: int,
    position: int = Query(0)
):
    """Add bookmark to list."""
    db = request.app.state.db

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO bookmark_list_items (list_id, bookmark_id, position)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (list_id, bookmark_id, position)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=400, detail="Could not add to list (may already exist)")

    return {"status": "added"}


@router.delete("/lists/{list_id}/items/{bookmark_id}")
@handle_endpoint_errors()
def remove_from_list(request: Request, list_id: int, bookmark_id: int):
    """Remove bookmark from list."""
    db = request.app.state.db

    with db.cursor() as cur:
        cur.execute(
            """
            DELETE FROM bookmark_list_items
            WHERE list_id = %s AND bookmark_id = %s
            """,
            (list_id, bookmark_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not in list")

    return {"status": "removed"}
