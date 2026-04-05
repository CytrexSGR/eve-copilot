"""
PI Chain Planner Service

Graph-based production chain management for PI plans.
Handles plan CRUD, target-to-node tree walking, node assignment,
and IST/SOLL status comparison.

Tables: pi_plans, pi_plan_nodes, pi_plan_edges (migration 107)
"""

import logging
from typing import List, Optional, Dict

from app.services.pi.models import PIChainNode

logger = logging.getLogger(__name__)


class ChainPlannerService:
    """Service for managing PI production chain plans.

    A plan is a DAG of nodes (PI materials at various tiers) connected by
    edges (parent-child production relationships).  Users add *targets*
    (final products); the service walks the PIChainNode tree returned by
    PISchematicService.get_production_chain() and upserts nodes/edges.

    DB pattern: ``with self.db.cursor() as cur:`` (RealDictCursor, auto-commit).
    """

    def __init__(self, db):
        self.db = db

    # ==================== Plan CRUD ====================

    def create_plan(self, name: str) -> dict:
        """Create a new PI chain plan.

        Args:
            name: Plan name (max 100 chars).

        Returns:
            Dict with plan id, name, status, timestamps.
        """
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_plans (name)
                VALUES (%s)
                RETURNING id, name, status, created_at, updated_at
            """, (name,))
            return cur.fetchone()

    def get_plan(self, plan_id: int) -> Optional[dict]:
        """Get a plan by ID including its nodes and edges.

        Returns:
            Dict with plan fields plus ``nodes`` and ``edges`` lists,
            or None if not found.
        """
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT id, name, status, created_at, updated_at
                FROM pi_plans
                WHERE id = %s
            """, (plan_id,))
            plan = cur.fetchone()

        if not plan:
            return None

        with self.db.cursor() as cur:
            cur.execute("""
                SELECT id, plan_id, type_id, type_name, tier,
                       is_target, soll_qty_per_hour, character_id, planet_id
                FROM pi_plan_nodes
                WHERE plan_id = %s
                ORDER BY tier DESC, type_name
            """, (plan_id,))
            nodes = cur.fetchall()

        with self.db.cursor() as cur:
            cur.execute("""
                SELECT id, plan_id, source_node_id, target_node_id, quantity_ratio
                FROM pi_plan_edges
                WHERE plan_id = %s
            """, (plan_id,))
            edges = cur.fetchall()

        return {
            **plan,
            "nodes": nodes,
            "edges": edges,
        }

    def list_plans(self, status: Optional[str] = None) -> List[dict]:
        """List all plans with summary counts.

        Args:
            status: Optional filter ('planning', 'active', 'paused', 'completed').

        Returns:
            List of plan dicts with node_count, target_count, assigned_count.
        """
        sql = """
            SELECT p.id, p.name, p.status, p.created_at, p.updated_at,
                COUNT(n.id) AS node_count,
                COUNT(n.id) FILTER (WHERE n.is_target) AS target_count,
                COUNT(n.id) FILTER (WHERE n.character_id IS NOT NULL) AS assigned_count
            FROM pi_plans p
            LEFT JOIN pi_plan_nodes n ON n.plan_id = p.id
        """
        params = []
        if status:
            sql += " WHERE p.status = %s"
            params.append(status)
        sql += " GROUP BY p.id ORDER BY p.created_at DESC"

        with self.db.cursor() as cur:
            cur.execute(sql, tuple(params))
            return cur.fetchall()

    def delete_plan(self, plan_id: int) -> bool:
        """Delete a plan (cascades to nodes and edges).

        Returns:
            True if deleted, False if not found.
        """
        with self.db.cursor() as cur:
            cur.execute("""
                DELETE FROM pi_plans
                WHERE id = %s
                RETURNING id
            """, (plan_id,))
            return cur.fetchone() is not None

    def update_plan_status(self, plan_id: int, status: str) -> bool:
        """Update a plan's status.

        Args:
            plan_id: The plan ID.
            status: New status.

        Returns:
            True if updated, False if plan not found.

        Raises:
            ValueError: If status is invalid.
        """
        valid = {"planning", "active", "paused", "completed"}
        if status not in valid:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid))}"
            )

        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE pi_plans
                SET status = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id
            """, (status, plan_id))
            return cur.fetchone() is not None

    # ==================== Target Management ====================

    def add_target(self, plan_id: int, chain: PIChainNode) -> dict:
        """Walk a PIChainNode tree and upsert nodes/edges into the plan.

        The root node is marked ``is_target = TRUE``.  Intermediate/leaf
        nodes are merged via ``ON CONFLICT (plan_id, type_id) DO UPDATE``
        which sums ``soll_qty_per_hour``.  RETURNING includes
        ``(xmax = 0) AS was_inserted`` to detect insert vs update.

        Args:
            plan_id: Target plan.
            chain: PIChainNode tree (from PISchematicService.get_production_chain).

        Returns:
            Dict with ``nodes_created``, ``nodes_merged``, ``edges_created``.
        """
        stats = {"nodes_created": 0, "nodes_merged": 0, "edges_created": 0}
        # Walk tree and collect node_id mapping (type_id -> db node id)
        node_id_map: Dict[int, int] = {}
        self._walk_tree(plan_id, chain, parent_node_id=None,
                        node_id_map=node_id_map, stats=stats)
        return stats

    def _walk_tree(
        self,
        plan_id: int,
        node: PIChainNode,
        parent_node_id: Optional[int],
        node_id_map: Dict[int, int],
        stats: dict,
    ) -> int:
        """Recursively upsert a PIChainNode and its children.

        Returns:
            The DB node id for this node.
        """
        is_target = parent_node_id is None  # root = target

        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_plan_nodes
                    (plan_id, type_id, type_name, tier, is_target, soll_qty_per_hour)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (plan_id, type_id) DO UPDATE SET
                    soll_qty_per_hour = pi_plan_nodes.soll_qty_per_hour + EXCLUDED.soll_qty_per_hour,
                    is_target = pi_plan_nodes.is_target OR EXCLUDED.is_target
                RETURNING id, (xmax = 0) AS was_inserted
            """, (
                plan_id, node.type_id, node.type_name, node.tier,
                is_target, node.quantity_needed,
            ))
            result = cur.fetchone()

        db_node_id = result["id"]
        was_inserted = result["was_inserted"]

        if was_inserted:
            stats["nodes_created"] += 1
        else:
            stats["nodes_merged"] += 1

        node_id_map[node.type_id] = db_node_id

        # Create edge from this node to its parent (if not root)
        if parent_node_id is not None:
            with self.db.cursor() as cur:
                cur.execute("""
                    INSERT INTO pi_plan_edges
                        (plan_id, source_node_id, target_node_id, quantity_ratio)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (plan_id, db_node_id, parent_node_id, node.quantity_needed))
            stats["edges_created"] += 1

        # Recurse into children
        for child in node.children:
            self._walk_tree(plan_id, child, db_node_id, node_id_map, stats)

        return db_node_id

    def remove_target(self, plan_id: int) -> List[dict]:
        """Remove all nodes and edges from a plan, returning remaining targets.

        The caller is expected to re-add remaining targets to rebuild the
        graph after removal.

        Returns:
            List of remaining target node dicts (empty after wipe).
        """
        with self.db.cursor() as cur:
            cur.execute(
                "DELETE FROM pi_plan_edges WHERE plan_id = %s", (plan_id,)
            )
            cur.execute(
                "DELETE FROM pi_plan_nodes WHERE plan_id = %s", (plan_id,)
            )
        return []

    # ==================== Node Assignment ====================

    def assign_node(
        self, plan_id: int, node_id: int,
        character_id: Optional[int], planet_id: Optional[int]
    ) -> Optional[dict]:
        """Assign a character + planet to a plan node.

        Args:
            plan_id: The plan ID (for scoping).
            node_id: The plan node ID.
            character_id: Character to assign (None to unassign).
            planet_id: Planet to assign (None to unassign).

        Returns:
            Updated node dict, or None if node not found.
        """
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE pi_plan_nodes
                SET character_id = %s, planet_id = %s
                WHERE id = %s AND plan_id = %s
                RETURNING id, plan_id, type_id, type_name, tier,
                          is_target, soll_qty_per_hour, character_id, planet_id
            """, (character_id, planet_id, node_id, plan_id))
            return cur.fetchone()

    # ==================== IST/SOLL Status Check ====================

    def get_status_check(self, plan_id: int) -> List[dict]:
        """Compare planned (SOLL) vs actual (IST) production for all nodes.

        For assigned nodes, queries ``pi_pins`` to find matching factories
        and computes IST qty/h as ``qty_per_cycle / cycle_time * 3600``.

        Status logic:
        - ``unassigned``: no character_id/planet_id
        - ``ok``: IST >= 90% of SOLL
        - ``warning``: IST >= 50% of SOLL
        - ``critical``: IST < 50% of SOLL

        Returns:
            List of node status dicts with soll, ist, status, delta_percent.
        """
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT id, type_id, type_name, tier, is_target,
                       soll_qty_per_hour, character_id, planet_id
                FROM pi_plan_nodes
                WHERE plan_id = %s
                ORDER BY tier DESC, type_name
            """, (plan_id,))
            nodes = cur.fetchall()

        results = []
        for node in nodes:
            soll = node["soll_qty_per_hour"]

            if not node["character_id"] or not node["planet_id"]:
                results.append({
                    **node,
                    "ist_qty_per_hour": 0,
                    "status": "unassigned",
                    "delta_percent": -100.0,
                })
                continue

            # Query pi_pins via pi_colonies JOIN for matching factory output
            with self.db.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(SUM(
                        CASE WHEN p.cycle_time > 0
                             THEN p.qty_per_cycle::float / p.cycle_time * 3600
                             ELSE 0
                        END
                    ), 0) AS ist_qty_per_hour
                    FROM pi_pins p
                    JOIN pi_colonies c ON c.id = p.colony_id
                    WHERE c.character_id = %s
                      AND c.planet_id = %s
                      AND p.product_type_id = %s
                      AND p.schematic_id IS NOT NULL
                """, (node["character_id"], node["planet_id"], node["type_id"]))
                pin_result = cur.fetchone()

            ist = float(pin_result["ist_qty_per_hour"]) if pin_result else 0

            if soll > 0:
                ratio = ist / soll
                delta_pct = round((ist - soll) / soll * 100, 1)
            else:
                ratio = 1.0 if ist >= 0 else 0
                delta_pct = 0.0

            if ratio >= 0.9:
                status = "ok"
            elif ratio >= 0.5:
                status = "warning"
            else:
                status = "critical"

            results.append({
                **node,
                "ist_qty_per_hour": round(ist, 2),
                "status": status,
                "delta_percent": delta_pct,
            })

        return results
