"""Production project service — manage multi-item manufacturing projects."""
import logging
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor

from eve_shared.constants import JITA_REGION_ID

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for managing production projects and their items."""

    def __init__(self, db):
        """Initialize with database pool."""
        self.db = db

    def list_projects(
        self, character_id: int, corporation_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List projects visible to a character (own + corporation).

        Returns projects ordered by most recently updated, with item counts.
        """
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    p.*,
                    (SELECT COUNT(*) FROM project_items pi WHERE pi.project_id = p.id) AS item_count
                FROM production_projects p
                WHERE p.creator_character_id = %s
                   OR p.corporation_id = %s
                ORDER BY p.updated_at DESC
                """,
                (character_id, corporation_id),
            )
            return cur.fetchall()

    def create_project(
        self,
        creator_character_id: int,
        name: str,
        description: str = "",
        corporation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new production project."""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO production_projects
                    (creator_character_id, name, description, corporation_id)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (creator_character_id, name, description, corporation_id),
            )
            return cur.fetchone()

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get a project with its items (including type names from SDE)."""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            # Get project row
            cur.execute(
                "SELECT * FROM production_projects WHERE id = %s",
                (project_id,),
            )
            project = cur.fetchone()
            if not project:
                return None

            # Get items with type names
            cur.execute(
                """
                SELECT
                    pi.*,
                    t."typeName" AS type_name
                FROM project_items pi
                LEFT JOIN "invTypes" t ON t."typeID" = pi.type_id
                WHERE pi.project_id = %s
                ORDER BY pi.added_at ASC
                """,
                (project_id,),
            )
            project["items"] = cur.fetchall()
            return project

    def update_project(self, project_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update project fields (name, description, status).

        Only updates provided fields. Always bumps updated_at.
        """
        allowed = {"name", "description", "status"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return self.get_project(project_id)

        set_parts = [f"{k} = %s" for k in fields]
        set_parts.append("updated_at = NOW()")
        values = list(fields.values()) + [project_id]

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                UPDATE production_projects
                SET {', '.join(set_parts)}
                WHERE id = %s
                RETURNING *
                """,
                values,
            )
            return cur.fetchone()

    def delete_project(self, project_id: int) -> bool:
        """Delete a project and all its items (CASCADE)."""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "DELETE FROM production_projects WHERE id = %s RETURNING id",
                (project_id,),
            )
            return cur.fetchone() is not None

    def add_item(
        self,
        project_id: int,
        type_id: int,
        quantity: int = 1,
        me_level: int = 0,
        te_level: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Add an item to a project. Resolves type_name via SDE.

        Auto-populates material decisions so the shopping list is
        filled from the start.
        """
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            # Insert the item
            cur.execute(
                """
                INSERT INTO project_items (project_id, type_id, quantity, me_level, te_level)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (project_id, type_id, quantity, me_level, te_level),
            )
            item = cur.fetchone()

            # Resolve type name
            cur.execute(
                'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                (type_id,),
            )
            row = cur.fetchone()
            item["type_name"] = row["typeName"] if row else "Unknown"

            # Bump project updated_at
            cur.execute(
                "UPDATE production_projects SET updated_at = NOW() WHERE id = %s",
                (project_id,),
            )

            # Auto-populate default material decisions (all leaves = buy)
            self._auto_populate_decisions(cur, item["id"], type_id)

            return item

    def _auto_populate_decisions(
        self, cur, item_id: int, type_id: int
    ) -> None:
        """Auto-populate material decisions for a project item.

        Builds the production chain and saves all leaf (non-manufacturable)
        materials as 'buy' decisions. This ensures the shopping list is
        populated immediately when an item is added.
        """
        try:
            from app.services.chains import ProductionChainService

            chain_svc = ProductionChainService(self.db)
            chain_data = chain_svc.get_chain_tree(type_id, quantity=1, format="flat")
            materials = chain_data.get("materials", [])

            if not materials:
                return

            values_list = []
            params = []
            for mat in materials:
                values_list.append("(%s, %s, 'buy', %s)")
                params.extend([item_id, mat["type_id"], mat["quantity"]])

            cur.execute(
                f"""
                INSERT INTO project_material_decisions
                    (project_item_id, material_type_id, decision, quantity)
                VALUES {', '.join(values_list)}
                ON CONFLICT (project_item_id, material_type_id) DO UPDATE
                SET quantity = EXCLUDED.quantity
                """,
                params,
            )
        except Exception as e:
            logger.warning(
                "Auto-populate decisions failed for item %s: %s", item_id, e
            )

    def update_item(self, item_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update item fields (quantity, me_level, te_level, status)."""
        allowed = {"quantity", "me_level", "te_level", "status"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            # Return current item if nothing to update
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM project_items WHERE id = %s", (item_id,))
                return cur.fetchone()

        set_parts = [f"{k} = %s" for k in fields]
        values = list(fields.values()) + [item_id]

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                UPDATE project_items
                SET {', '.join(set_parts)}
                WHERE id = %s
                RETURNING *
                """,
                values,
            )
            return cur.fetchone()

    def delete_item(self, item_id: int) -> bool:
        """Delete an item from a project."""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "DELETE FROM project_items WHERE id = %s RETURNING id",
                (item_id,),
            )
            return cur.fetchone() is not None

    def get_decisions(self, item_id: int) -> List[Dict[str, Any]]:
        """Get material decisions for a project item with type names."""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    d.*,
                    t."typeName" AS type_name
                FROM project_material_decisions d
                LEFT JOIN "invTypes" t ON t."typeID" = d.material_type_id
                WHERE d.project_item_id = %s
                ORDER BY d.material_type_id
                """,
                (item_id,),
            )
            return cur.fetchall()

    def save_decisions(
        self, item_id: int, decisions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Replace all material decisions for a project item.

        Deletes existing decisions and inserts the new batch.
        Simpler than upsert for full replacement scenarios.
        """
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            # Delete existing decisions
            cur.execute(
                "DELETE FROM project_material_decisions WHERE project_item_id = %s",
                (item_id,),
            )

            if not decisions:
                return []

            # Batch insert new decisions
            values_list = []
            params = []
            for d in decisions:
                values_list.append("(%s, %s, %s, %s)")
                params.extend([
                    item_id,
                    d["material_type_id"],
                    d["decision"],
                    d["quantity"],
                ])

            cur.execute(
                f"""
                INSERT INTO project_material_decisions
                    (project_item_id, material_type_id, decision, quantity)
                VALUES {', '.join(values_list)}
                RETURNING *
                """,
                params,
            )
            return cur.fetchall()

    def get_shopping_list(self, project_id: int) -> Dict[str, Any]:
        """Aggregate all 'buy' decisions across all project items.

        Joins with invTypes for names and market_prices for Jita sell prices.
        Also tracks which item names need each material (needed_by).
        Returns {"items": [...], "total_cost": float}.
        """
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    d.material_type_id,
                    t."typeName" AS type_name,
                    SUM(d.quantity * pi.quantity) AS total_quantity,
                    COALESCE(mp.lowest_sell, 0) AS unit_price,
                    ARRAY_AGG(DISTINCT item_types."typeName") AS needed_by
                FROM project_material_decisions d
                JOIN project_items pi ON pi.id = d.project_item_id
                LEFT JOIN "invTypes" t ON t."typeID" = d.material_type_id
                LEFT JOIN "invTypes" item_types ON item_types."typeID" = pi.type_id
                LEFT JOIN market_prices mp
                    ON mp.type_id = d.material_type_id AND mp.region_id = %s
                WHERE pi.project_id = %s
                  AND d.decision = 'buy'
                GROUP BY d.material_type_id, t."typeName", mp.lowest_sell
                ORDER BY t."typeName"
                """,
                (JITA_REGION_ID, project_id),
            )
            rows = cur.fetchall()

        total_cost = 0.0
        items = []
        for row in rows:
            qty = int(row["total_quantity"])
            price = float(row["unit_price"] or 0)
            line_total = price * qty
            total_cost += line_total

            items.append({
                "type_id": row["material_type_id"],
                "type_name": row["type_name"],
                "total_quantity": qty,
                "unit_price": price,
                "total_price": round(line_total, 2),
                "needed_by": row["needed_by"],
            })

        return {
            "items": items,
            "total_cost": round(total_cost, 2),
        }
