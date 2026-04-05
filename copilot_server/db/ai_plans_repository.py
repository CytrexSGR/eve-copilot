# copilot_server/db/ai_plans_repository.py
"""
Database repository for AI Copilot plans and context.
"""

import logging
from datetime import datetime
from typing import Optional, List
import asyncpg

logger = logging.getLogger(__name__)


class AIPlanRepository:
    """Repository for AI plans CRUD operations."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    # ==================== PLANS ====================

    async def create_plan(
        self,
        character_id: int,
        title: str,
        goal_type: str,
        description: Optional[str] = None,
        target_data: dict = None,
        target_date: Optional[datetime] = None,
    ) -> int:
        """Create a new plan and return its ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO ai_plans (character_id, title, description, goal_type, target_data, target_date)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                character_id,
                title,
                description,
                goal_type,
                target_data or {},
                target_date,
            )
            return row["id"]

    async def get_plan(self, plan_id: int) -> Optional[dict]:
        """Get a plan by ID with milestones and resources."""
        async with self.pool.acquire() as conn:
            plan = await conn.fetchrow(
                "SELECT * FROM ai_plans WHERE id = $1", plan_id
            )
            if not plan:
                return None

            milestones = await conn.fetch(
                "SELECT * FROM ai_plan_milestones WHERE plan_id = $1 ORDER BY sequence_order",
                plan_id,
            )
            resources = await conn.fetch(
                "SELECT * FROM ai_plan_resources WHERE plan_id = $1", plan_id
            )

            return {
                **dict(plan),
                "milestones": [dict(m) for m in milestones],
                "resources": [dict(r) for r in resources],
            }

    async def list_plans(
        self,
        character_id: int,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        """List plans for a character."""
        async with self.pool.acquire() as conn:
            if status:
                plans = await conn.fetch(
                    """
                    SELECT * FROM ai_plans
                    WHERE character_id = $1 AND status = $2
                    ORDER BY updated_at DESC
                    LIMIT $3
                    """,
                    character_id,
                    status,
                    limit,
                )
            else:
                plans = await conn.fetch(
                    """
                    SELECT * FROM ai_plans
                    WHERE character_id = $1
                    ORDER BY updated_at DESC
                    LIMIT $2
                    """,
                    character_id,
                    limit,
                )

            if not plans:
                return []

            # Batch fetch milestones and resources (3 queries total instead of 1 + N*2)
            plan_ids = [p["id"] for p in plans]

            milestones = await conn.fetch(
                """
                SELECT * FROM ai_plan_milestones
                WHERE plan_id = ANY($1)
                ORDER BY plan_id, sequence_order
                """,
                plan_ids,
            )

            resources = await conn.fetch(
                "SELECT * FROM ai_plan_resources WHERE plan_id = ANY($1)",
                plan_ids,
            )

            # Group by plan_id
            milestones_by_plan = {}
            for m in milestones:
                pid = m["plan_id"]
                if pid not in milestones_by_plan:
                    milestones_by_plan[pid] = []
                milestones_by_plan[pid].append(dict(m))

            resources_by_plan = {}
            for r in resources:
                pid = r["plan_id"]
                if pid not in resources_by_plan:
                    resources_by_plan[pid] = []
                resources_by_plan[pid].append(dict(r))

            # Assemble results
            return [
                {
                    **dict(plan),
                    "milestones": milestones_by_plan.get(plan["id"], []),
                    "resources": resources_by_plan.get(plan["id"], []),
                }
                for plan in plans
            ]

    async def update_plan(self, plan_id: int, **kwargs) -> bool:
        """Update plan fields."""
        if not kwargs:
            return False

        # Build dynamic update query
        fields = []
        values = []
        idx = 1
        for key, value in kwargs.items():
            if key in ("title", "description", "status", "progress_pct", "target_date", "target_data"):
                fields.append(f"{key} = ${idx}")
                values.append(value)
                idx += 1

        if not fields:
            return False

        fields.append(f"updated_at = ${idx}")
        values.append(datetime.now())
        idx += 1

        # Handle completion
        if kwargs.get("status") == "completed":
            fields.append(f"completed_at = ${idx}")
            values.append(datetime.now())
            idx += 1

        values.append(plan_id)

        async with self.pool.acquire() as conn:
            result = await conn.execute(
                f"UPDATE ai_plans SET {', '.join(fields)} WHERE id = ${idx}",
                *values,
            )
            return result == "UPDATE 1"

    async def delete_plan(self, plan_id: int) -> bool:
        """Delete a plan (cascades to milestones and resources)."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM ai_plans WHERE id = $1", plan_id
            )
            return result == "DELETE 1"

    # ==================== MILESTONES ====================

    async def add_milestone(
        self,
        plan_id: int,
        title: str,
        description: Optional[str] = None,
        sequence_order: int = 0,
        tracking_type: Optional[str] = None,
        tracking_config: dict = None,
        target_value: Optional[float] = None,
    ) -> int:
        """Add a milestone to a plan."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO ai_plan_milestones
                (plan_id, title, description, sequence_order, tracking_type, tracking_config, target_value)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                plan_id,
                title,
                description,
                sequence_order,
                tracking_type,
                tracking_config or {},
                target_value,
            )
            return row["id"]

    async def update_milestone(self, milestone_id: int, **kwargs) -> bool:
        """Update milestone fields."""
        if not kwargs:
            return False

        fields = []
        values = []
        idx = 1
        for key, value in kwargs.items():
            if key in ("title", "description", "status", "current_value", "tracking_config"):
                fields.append(f"{key} = ${idx}")
                values.append(value)
                idx += 1

        if not fields:
            return False

        # Add updated_at
        fields.append(f"updated_at = ${idx}")
        values.append(datetime.now())
        idx += 1

        # Handle completion
        if kwargs.get("status") == "completed":
            fields.append(f"completed_at = ${idx}")
            values.append(datetime.now())
            idx += 1

        values.append(milestone_id)

        async with self.pool.acquire() as conn:
            result = await conn.execute(
                f"UPDATE ai_plan_milestones SET {', '.join(fields)} WHERE id = ${idx}",
                *values,
            )
            return result == "UPDATE 1"

    async def delete_milestone(self, milestone_id: int) -> bool:
        """Delete a milestone."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM ai_plan_milestones WHERE id = $1", milestone_id
            )
            return result == "DELETE 1"

    # ==================== RESOURCES ====================

    async def link_resource(
        self, plan_id: int, resource_type: str, resource_id: int
    ) -> int:
        """Link a resource to a plan."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO ai_plan_resources (plan_id, resource_type, resource_id)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                plan_id,
                resource_type,
                resource_id,
            )
            return row["id"]

    async def unlink_resource(self, resource_link_id: int) -> bool:
        """Unlink a resource from a plan."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM ai_plan_resources WHERE id = $1", resource_link_id
            )
            return result == "DELETE 1"


class AIContextRepository:
    """Repository for AI context operations."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def set_context(
        self,
        character_id: int,
        context_key: str,
        context_value: dict,
        source: str = "user_stated",
        confidence: float = 1.0,
        expires_at: Optional[datetime] = None,
    ) -> int:
        """Set or update a context value."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO ai_context (character_id, context_key, context_value, source, confidence, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (character_id, context_key)
                DO UPDATE SET
                    context_value = EXCLUDED.context_value,
                    source = EXCLUDED.source,
                    confidence = EXCLUDED.confidence,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = NOW()
                RETURNING id
                """,
                character_id,
                context_key,
                context_value,
                source,
                confidence,
                expires_at,
            )
            return row["id"]

    async def get_context(self, character_id: int) -> List[dict]:
        """Get all non-expired context for a character."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM ai_context
                WHERE character_id = $1
                AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY updated_at DESC
                """,
                character_id,
            )
            return [dict(r) for r in rows]

    async def delete_context(self, character_id: int, context_key: str) -> bool:
        """Delete a specific context key."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM ai_context WHERE character_id = $1 AND context_key = $2",
                character_id,
                context_key,
            )
            return result == "DELETE 1"


class AISessionSummaryRepository:
    """Repository for session summaries."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create_summary(
        self,
        session_id: str,
        character_id: int,
        summary: str,
        key_decisions: List[str] = None,
        open_questions: List[str] = None,
        active_plan_ids: List[int] = None,
    ) -> int:
        """Create a session summary."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO ai_session_summaries
                (session_id, character_id, summary, key_decisions, open_questions, active_plan_ids)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                session_id,
                character_id,
                summary,
                key_decisions or [],
                open_questions or [],
                active_plan_ids or [],
            )
            return row["id"]

    async def get_latest_summary(self, character_id: int) -> Optional[dict]:
        """Get the most recent session summary for a character."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM ai_session_summaries
                WHERE character_id = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                character_id,
            )
            return dict(row) if row else None

    async def get_session_summary(self, session_id: str) -> Optional[dict]:
        """Get summary for a specific session."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ai_session_summaries WHERE session_id = $1",
                session_id,
            )
            return dict(row) if row else None
