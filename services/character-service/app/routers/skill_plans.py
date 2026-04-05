"""
Skill Plans API Router
CRUD operations for skill plans + calculation endpoints.
Migrated from monolith to character-service.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional, List
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor

from app.services.skill_planner_service import skill_planner_service

router = APIRouter()


# === Pydantic Models ===

class PlanCreate(BaseModel):
    character_id: int
    name: str
    description: Optional[str] = None

class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class PlanItemCreate(BaseModel):
    skill_type_id: int
    target_level: int = Field(ge=1, le=5, description="Skill level 1-5")

class PlanItemUpdate(BaseModel):
    target_level: Optional[int] = Field(default=None, ge=1, le=5, description="Skill level 1-5")
    sort_order: Optional[int] = None
    notes: Optional[str] = None

class ReorderRequest(BaseModel):
    item_ids: List[int]  # New order

class RemapCreate(BaseModel):
    after_item_id: Optional[int] = None
    perception: int = Field(default=20, ge=17, le=27, description="17-27")
    memory: int = Field(default=20, ge=17, le=27, description="17-27")
    willpower: int = Field(default=20, ge=17, le=27, description="17-27")
    intelligence: int = Field(default=20, ge=17, le=27, description="17-27")
    charisma: int = Field(default=19, ge=17, le=27, description="17-27")


# === Plan CRUD ===

@router.post("")
def create_plan(request: Request, plan: PlanCreate):
    """Create a new skill plan."""
    db = request.app.state.db
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            INSERT INTO skill_plans (character_id, name, description)
            VALUES (%s, %s, %s)
            RETURNING id, character_id, name, description, created_at
        """, (plan.character_id, plan.name, plan.description))
        result = cur.fetchone()
        # commit handled by context manager
    return result


@router.get("")
def list_plans(request: Request, character_id: Optional[int] = None):
    """List all skill plans, optionally filtered by character."""
    db = request.app.state.db
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        if character_id:
            cur.execute("""
                SELECT p.*, COUNT(i.id) as skill_count
                FROM skill_plans p
                LEFT JOIN skill_plan_items i ON i.plan_id = p.id
                WHERE p.character_id = %s
                GROUP BY p.id
                ORDER BY p.updated_at DESC
            """, (character_id,))
        else:
            cur.execute("""
                SELECT p.*, COUNT(i.id) as skill_count
                FROM skill_plans p
                LEFT JOIN skill_plan_items i ON i.plan_id = p.id
                GROUP BY p.id
                ORDER BY p.updated_at DESC
            """)
        return cur.fetchall()


@router.get("/{plan_id}")
def get_plan(request: Request, plan_id: int):
    """Get plan with all items."""
    db = request.app.state.db
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Get plan
        cur.execute("SELECT * FROM skill_plans WHERE id = %s", (plan_id,))
        plan = cur.fetchone()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Get items with skill names
        cur.execute("""
            SELECT i.*, t."typeName" as skill_name
            FROM skill_plan_items i
            LEFT JOIN "invTypes" t ON t."typeID" = i.skill_type_id
            WHERE i.plan_id = %s
            ORDER BY i.sort_order
        """, (plan_id,))
        items = cur.fetchall()

        # Get remaps
        cur.execute("""
            SELECT * FROM skill_plan_remaps WHERE plan_id = %s
        """, (plan_id,))
        remaps = cur.fetchall()

    return {**plan, 'items': items, 'remaps': remaps}


@router.put("/{plan_id}")
def update_plan(request: Request, plan_id: int, plan: PlanUpdate):
    """Update plan metadata."""
    updates = []
    values = []
    if plan.name is not None:
        updates.append("name = %s")
        values.append(plan.name)
    if plan.description is not None:
        updates.append("description = %s")
        values.append(plan.description)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = NOW()")
    values.append(plan_id)

    db = request.app.state.db
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""
            UPDATE skill_plans SET {', '.join(updates)}
            WHERE id = %s
            RETURNING *
        """, values)
        result = cur.fetchone()
        # commit handled by context manager

    if not result:
        raise HTTPException(status_code=404, detail="Plan not found")
    return result


@router.delete("/{plan_id}")
def delete_plan(request: Request, plan_id: int):
    """Delete a plan."""
    db = request.app.state.db
    with db.cursor() as cur:
        cur.execute("DELETE FROM skill_plans WHERE id = %s RETURNING id", (plan_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Plan not found")
        # commit handled by context manager
    return {"deleted": plan_id}


# === Plan Items ===

@router.post("/{plan_id}/items")
def add_item(request: Request, plan_id: int, item: PlanItemCreate):
    """Add skill to plan."""
    db = request.app.state.db
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Get max sort order
        cur.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 as next FROM skill_plan_items WHERE plan_id = %s", (plan_id,))
        next_order = cur.fetchone()['next']

        cur.execute("""
            INSERT INTO skill_plan_items (plan_id, skill_type_id, target_level, sort_order)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """, (plan_id, item.skill_type_id, item.target_level, next_order))
        result = cur.fetchone()

        # Update plan timestamp
        cur.execute("UPDATE skill_plans SET updated_at = NOW() WHERE id = %s", (plan_id,))
        # commit handled by context manager
    return result


@router.post("/{plan_id}/items/batch")
def add_items_batch(request: Request, plan_id: int, items: List[PlanItemCreate]):
    """Add multiple skills to plan."""
    db = request.app.state.db
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Get max sort order
        cur.execute("SELECT COALESCE(MAX(sort_order), 0) as max FROM skill_plan_items WHERE plan_id = %s", (plan_id,))
        start_order = cur.fetchone()['max'] + 1

        results = []
        for i, item in enumerate(items):
            cur.execute("""
                INSERT INTO skill_plan_items (plan_id, skill_type_id, target_level, sort_order)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (plan_id, skill_type_id, target_level) DO NOTHING
                RETURNING *
            """, (plan_id, item.skill_type_id, item.target_level, start_order + i))
            row = cur.fetchone()
            if row:
                results.append(row)

        cur.execute("UPDATE skill_plans SET updated_at = NOW() WHERE id = %s", (plan_id,))
        # commit handled by context manager
    return results


@router.put("/{plan_id}/items/{item_id}")
def update_item(request: Request, plan_id: int, item_id: int, item: PlanItemUpdate):
    """Update a plan item."""
    updates = []
    values = []
    if item.target_level is not None:
        updates.append("target_level = %s")
        values.append(item.target_level)
    if item.sort_order is not None:
        updates.append("sort_order = %s")
        values.append(item.sort_order)
    if item.notes is not None:
        updates.append("notes = %s")
        values.append(item.notes)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    values.extend([item_id, plan_id])

    db = request.app.state.db
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""
            UPDATE skill_plan_items SET {', '.join(updates)}
            WHERE id = %s AND plan_id = %s
            RETURNING *
        """, values)
        result = cur.fetchone()
        # commit handled by context manager

    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.delete("/{plan_id}/items/{item_id}")
def delete_item(request: Request, plan_id: int, item_id: int):
    """Remove skill from plan."""
    db = request.app.state.db
    with db.cursor() as cur:
        cur.execute("DELETE FROM skill_plan_items WHERE id = %s AND plan_id = %s RETURNING id", (item_id, plan_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Item not found")
        cur.execute("UPDATE skill_plans SET updated_at = NOW() WHERE id = %s", (plan_id,))
        # commit handled by context manager
    return {"deleted": item_id}


@router.post("/{plan_id}/reorder")
def reorder_items(request: Request, plan_id: int, reorder_request: ReorderRequest):
    """Reorder plan items."""
    db = request.app.state.db
    with db.cursor() as cur:
        for i, item_id in enumerate(reorder_request.item_ids):
            cur.execute("""
                UPDATE skill_plan_items SET sort_order = %s
                WHERE id = %s AND plan_id = %s
            """, (i + 1, item_id, plan_id))
        cur.execute("UPDATE skill_plans SET updated_at = NOW() WHERE id = %s", (plan_id,))
        # commit handled by context manager
    return {"reordered": len(reorder_request.item_ids)}


# === Remaps ===

@router.post("/{plan_id}/remaps")
def add_remap(request: Request, plan_id: int, remap: RemapCreate):
    """Add remap point to plan."""
    total = remap.perception + remap.memory + remap.willpower + remap.intelligence + remap.charisma
    if total != 99:
        raise HTTPException(status_code=400, detail=f"Attributes must sum to 99, got {total}")

    db = request.app.state.db
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            INSERT INTO skill_plan_remaps (plan_id, after_item_id, perception, memory, willpower, intelligence, charisma)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (plan_id, remap.after_item_id, remap.perception, remap.memory, remap.willpower, remap.intelligence, remap.charisma))
        result = cur.fetchone()
        # commit handled by context manager
    return result


@router.delete("/{plan_id}/remaps/{remap_id}")
def delete_remap(request: Request, plan_id: int, remap_id: int):
    """Remove remap from plan."""
    db = request.app.state.db
    with db.cursor() as cur:
        cur.execute("DELETE FROM skill_plan_remaps WHERE id = %s AND plan_id = %s RETURNING id", (remap_id, plan_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Remap not found")
        # commit handled by context manager
    return {"deleted": remap_id}


# === Calculations ===

@router.get("/{plan_id}/calculate")
def calculate_plan(request: Request, plan_id: int, character_id: int = Query(...)):
    """Calculate training times for plan with character's attributes."""
    from app.services import CharacterService

    service = CharacterService(request.app.state.db, request.app.state.redis)

    # Get character attributes
    attrs_response = service.get_attributes(character_id)
    if not attrs_response:
        raise HTTPException(status_code=400, detail="Could not get character attributes")

    attributes = {
        'perception': attrs_response.perception,
        'memory': attrs_response.memory,
        'willpower': attrs_response.willpower,
        'intelligence': attrs_response.intelligence,
        'charisma': attrs_response.charisma,
    }

    # Get implant bonuses
    implants_response = service.get_implants(character_id)
    implant_bonuses = {'perception': 0, 'memory': 0, 'willpower': 0, 'intelligence': 0, 'charisma': 0}
    if implants_response and implants_response.implants:
        for implant in implants_response.implants:
            if implant.perception_bonus:
                implant_bonuses['perception'] += implant.perception_bonus
            if implant.memory_bonus:
                implant_bonuses['memory'] += implant.memory_bonus
            if implant.willpower_bonus:
                implant_bonuses['willpower'] += implant.willpower_bonus
            if implant.intelligence_bonus:
                implant_bonuses['intelligence'] += implant.intelligence_bonus
            if implant.charisma_bonus:
                implant_bonuses['charisma'] += implant.charisma_bonus

    result = skill_planner_service.calculate_plan(request, plan_id, character_id, attributes, implant_bonuses)
    result['current_attributes'] = attributes
    result['implant_bonuses'] = implant_bonuses

    return result
