# app/services/trading/goals.py
"""Trading goals service for daily/weekly/monthly targets.

Migrated from monolith to market-service.
Uses request.app.state.db for database access.
"""

import logging
from datetime import datetime, date, timezone, timedelta
from typing import List, Optional, Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TradingGoal(BaseModel):
    """Trading goal model."""
    id: int = Field(default=0)
    character_id: int
    goal_type: str  # daily, weekly, monthly
    target_type: str = Field(default="profit")  # profit, volume, trades, roi
    target_value: float
    current_value: float = Field(default=0)
    period_start: date
    period_end: date
    is_achieved: bool = Field(default=False)
    achieved_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
    notify_on_progress: bool = Field(default=True)
    notify_on_completion: bool = Field(default=True)
    type_id: Optional[int] = None
    type_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GoalProgress(BaseModel):
    """Goal progress tracking."""
    goal: TradingGoal
    progress_percent: float
    remaining: float
    days_remaining: int
    on_track: bool  # If progress pace will meet target by end
    projected_value: float  # Projected final value at current pace


class GoalsResponse(BaseModel):
    """Response for goals list with progress."""
    character_id: int
    active_goals: List[GoalProgress] = Field(default_factory=list)
    completed_today: int = Field(default=0)
    completed_this_week: int = Field(default=0)
    completed_this_month: int = Field(default=0)
    total_achievements: int = Field(default=0)


class TradingGoalsService:
    """Service for managing trading goals.

    Adapted for market-service to use eve_shared database pool.
    """

    def __init__(self, db_pool):
        """Initialize with database pool.

        Args:
            db_pool: Database connection pool (eve_shared)
        """
        self.db = db_pool

    def _get_period_bounds(self, goal_type: str, ref_date: date = None) -> tuple[date, date]:
        """Calculate period start and end dates.

        Args:
            goal_type: daily, weekly, or monthly
            ref_date: Reference date (defaults to today)

        Returns:
            Tuple of (period_start, period_end)
        """
        if ref_date is None:
            ref_date = date.today()

        if goal_type == "daily":
            return ref_date, ref_date

        elif goal_type == "weekly":
            # Week starts on Monday
            start = ref_date - timedelta(days=ref_date.weekday())
            end = start + timedelta(days=6)
            return start, end

        elif goal_type == "monthly":
            start = ref_date.replace(day=1)
            # Last day of month
            if ref_date.month == 12:
                end = date(ref_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(ref_date.year, ref_date.month + 1, 1) - timedelta(days=1)
            return start, end

        else:
            raise ValueError(f"Unknown goal_type: {goal_type}")

    def create_goal(
        self,
        character_id: int,
        goal_type: str,
        target_type: str,
        target_value: float,
        type_id: Optional[int] = None,
        type_name: Optional[str] = None,
        notify_on_progress: bool = True,
        notify_on_completion: bool = True
    ) -> TradingGoal:
        """Create a new trading goal.

        Args:
            character_id: Character ID
            goal_type: daily, weekly, or monthly
            target_type: profit, volume, trades, or roi
            target_value: Target value for the goal
            type_id: Optional specific item type
            type_name: Optional item name
            notify_on_progress: Alert at milestones
            notify_on_completion: Alert when goal reached

        Returns:
            Created TradingGoal
        """
        period_start, period_end = self._get_period_bounds(goal_type)

        with self.db.cursor() as cur:
            # Check for existing goal of same type in same period
            cur.execute("""
                SELECT id FROM trading_goals
                WHERE character_id = %s
                  AND goal_type = %s
                  AND target_type = %s
                  AND COALESCE(type_id, 0) = COALESCE(%s, 0)
                  AND period_start = %s
            """, (character_id, goal_type, target_type, type_id, period_start))

            existing = cur.fetchone()
            if existing:
                # Update existing goal
                cur.execute("""
                    UPDATE trading_goals
                    SET target_value = %s, type_name = %s,
                        notify_on_progress = %s, notify_on_completion = %s,
                        is_active = TRUE
                    WHERE id = %s
                    RETURNING id, current_value, is_achieved, achieved_at, created_at
                """, (target_value, type_name, notify_on_progress, notify_on_completion, existing['id']))
                row = cur.fetchone()

                return TradingGoal(
                    id=row['id'],
                    character_id=character_id,
                    goal_type=goal_type,
                    target_type=target_type,
                    target_value=target_value,
                    current_value=float(row['current_value'] or 0),
                    period_start=period_start,
                    period_end=period_end,
                    is_achieved=row['is_achieved'],
                    achieved_at=row['achieved_at'],
                    is_active=True,
                    notify_on_progress=notify_on_progress,
                    notify_on_completion=notify_on_completion,
                    type_id=type_id,
                    type_name=type_name,
                    created_at=row['created_at']
                )

            # Insert new goal
            cur.execute("""
                INSERT INTO trading_goals
                (character_id, goal_type, target_type, target_value, period_start, period_end,
                 type_id, type_name, notify_on_progress, notify_on_completion, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                RETURNING id, created_at
            """, (
                character_id, goal_type, target_type, target_value,
                period_start, period_end, type_id, type_name,
                notify_on_progress, notify_on_completion
            ))

            row = cur.fetchone()

            return TradingGoal(
                id=row['id'],
                character_id=character_id,
                goal_type=goal_type,
                target_type=target_type,
                target_value=target_value,
                current_value=0,
                period_start=period_start,
                period_end=period_end,
                is_active=True,
                notify_on_progress=notify_on_progress,
                notify_on_completion=notify_on_completion,
                type_id=type_id,
                type_name=type_name,
                created_at=row['created_at']
            )

    def get_goals(
        self,
        character_id: int,
        active_only: bool = True,
        goal_type: Optional[str] = None
    ) -> GoalsResponse:
        """Get all goals with progress for a character.

        Args:
            character_id: Character ID
            active_only: Only return active goals
            goal_type: Filter by goal type

        Returns:
            GoalsResponse with goals and statistics
        """
        today = date.today()

        with self.db.cursor() as cur:
            # Build query
            where = ["character_id = %s"]
            params: List[Any] = [character_id]

            if active_only:
                where.append("is_active = TRUE")
                where.append("period_end >= %s")
                params.append(today)

            if goal_type:
                where.append("goal_type = %s")
                params.append(goal_type)

            cur.execute(f"""
                SELECT id, goal_type, target_type, target_value, current_value,
                       period_start, period_end, is_achieved, achieved_at,
                       is_active, notify_on_progress, notify_on_completion,
                       type_id, type_name, created_at
                FROM trading_goals
                WHERE {' AND '.join(where)}
                ORDER BY
                    CASE goal_type
                        WHEN 'daily' THEN 1
                        WHEN 'weekly' THEN 2
                        WHEN 'monthly' THEN 3
                    END,
                    target_type
            """, params)

            goals = []
            for row in cur.fetchall():
                goal = TradingGoal(
                    id=row['id'],
                    character_id=character_id,
                    goal_type=row['goal_type'],
                    target_type=row['target_type'],
                    target_value=float(row['target_value']),
                    current_value=float(row['current_value'] or 0),
                    period_start=row['period_start'],
                    period_end=row['period_end'],
                    is_achieved=row['is_achieved'],
                    achieved_at=row['achieved_at'],
                    is_active=row['is_active'],
                    notify_on_progress=row['notify_on_progress'],
                    notify_on_completion=row['notify_on_completion'],
                    type_id=row['type_id'],
                    type_name=row['type_name'],
                    created_at=row['created_at']
                )

                # Calculate progress
                progress_percent = 0.0
                if goal.target_value > 0:
                    progress_percent = min(100.0, (goal.current_value / goal.target_value) * 100)

                remaining = max(0, goal.target_value - goal.current_value)

                # Days remaining in period
                days_remaining = max(0, (goal.period_end - today).days + 1)
                days_elapsed = max(1, (today - goal.period_start).days + 1)
                total_days = (goal.period_end - goal.period_start).days + 1

                # Projected value at current pace
                if days_elapsed > 0:
                    daily_rate = goal.current_value / days_elapsed
                    projected_value = daily_rate * total_days
                else:
                    projected_value = 0

                on_track = projected_value >= goal.target_value

                goals.append(GoalProgress(
                    goal=goal,
                    progress_percent=round(progress_percent, 1),
                    remaining=remaining,
                    days_remaining=days_remaining,
                    on_track=on_track,
                    projected_value=round(projected_value, 2)
                ))

            # Get achievement counts - use column aliases for dict access
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE achieved_at::date = %s) AS completed_today,
                    COUNT(*) FILTER (WHERE achieved_at >= date_trunc('week', %s::date)) AS completed_this_week,
                    COUNT(*) FILTER (WHERE achieved_at >= date_trunc('month', %s::date)) AS completed_this_month,
                    COUNT(*) AS total_achievements
                FROM trading_goals
                WHERE character_id = %s AND is_achieved = TRUE
            """, (today, today, today, character_id))

            counts = cur.fetchone()

            return GoalsResponse(
                character_id=character_id,
                active_goals=goals,
                completed_today=counts['completed_today'] or 0,
                completed_this_week=counts['completed_this_week'] or 0,
                completed_this_month=counts['completed_this_month'] or 0,
                total_achievements=counts['total_achievements'] or 0
            )

    def update_goal_progress(
        self,
        goal_id: int,
        current_value: float
    ) -> Optional[TradingGoal]:
        """Update progress for a specific goal.

        Args:
            goal_id: Goal ID
            current_value: New current value

        Returns:
            Updated TradingGoal or None if not found
        """
        with self.db.cursor() as cur:
            # Get goal and check if achieved
            cur.execute("""
                SELECT target_value, is_achieved FROM trading_goals WHERE id = %s
            """, (goal_id,))

            row = cur.fetchone()
            if not row:
                return None

            target_value = float(row['target_value'])
            was_achieved = row['is_achieved']

            # Check if now achieved
            is_achieved = current_value >= target_value
            achieved_at = datetime.now(timezone.utc) if is_achieved and not was_achieved else None

            # Update
            if achieved_at:
                cur.execute("""
                    UPDATE trading_goals
                    SET current_value = %s, is_achieved = TRUE, achieved_at = %s
                    WHERE id = %s
                    RETURNING character_id, goal_type, target_type, period_start, period_end,
                              is_active, notify_on_progress, notify_on_completion,
                              type_id, type_name, created_at
                """, (current_value, achieved_at, goal_id))
            else:
                cur.execute("""
                    UPDATE trading_goals
                    SET current_value = %s
                    WHERE id = %s
                    RETURNING character_id, goal_type, target_type, period_start, period_end,
                              is_active, notify_on_progress, notify_on_completion,
                              type_id, type_name, created_at
                """, (current_value, goal_id))

            row = cur.fetchone()

            return TradingGoal(
                id=goal_id,
                character_id=row['character_id'],
                goal_type=row['goal_type'],
                target_type=row['target_type'],
                target_value=target_value,
                current_value=current_value,
                period_start=row['period_start'],
                period_end=row['period_end'],
                is_achieved=is_achieved,
                achieved_at=achieved_at,
                is_active=row['is_active'],
                notify_on_progress=row['notify_on_progress'],
                notify_on_completion=row['notify_on_completion'],
                type_id=row['type_id'],
                type_name=row['type_name'],
                created_at=row['created_at']
            )

    def delete_goal(self, goal_id: int, character_id: int) -> bool:
        """Delete a trading goal.

        Args:
            goal_id: Goal ID
            character_id: Character ID (for verification)

        Returns:
            True if deleted, False if not found
        """
        with self.db.cursor() as cur:
            cur.execute("""
                DELETE FROM trading_goals
                WHERE id = %s AND character_id = %s
            """, (goal_id, character_id))

            return cur.rowcount > 0

    def deactivate_goal(self, goal_id: int, character_id: int) -> bool:
        """Deactivate a trading goal (soft delete).

        Args:
            goal_id: Goal ID
            character_id: Character ID (for verification)

        Returns:
            True if deactivated, False if not found
        """
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE trading_goals
                SET is_active = FALSE
                WHERE id = %s AND character_id = %s
            """, (goal_id, character_id))

            return cur.rowcount > 0

    def sync_goal_progress(self, character_id: int, trading_service) -> List[GoalProgress]:
        """Sync all active goals with current trading data.

        Args:
            character_id: Character ID
            trading_service: TradingAnalyticsService instance for data

        Returns:
            List of updated goal progress
        """
        # Get active goals
        goals_response = self.get_goals(character_id, active_only=True)

        # Get current trading data
        try:
            pnl_report = trading_service.calculate_pnl(character_id, include_corp=True, days=31)
        except Exception as e:
            logger.error(f"Failed to get P&L data for goal sync: {e}")
            return goals_response.active_goals

        updated_goals = []

        for goal_progress in goals_response.active_goals:
            goal = goal_progress.goal

            # Calculate current value based on target type
            current_value = 0.0

            if goal.target_type == "profit":
                # Sum profit in the goal's period
                current_value = pnl_report.total_realized_pnl

            elif goal.target_type == "volume":
                # Sum volume traded in period
                for item in pnl_report.items:
                    current_value += item.total_sold

            elif goal.target_type == "trades":
                # Count distinct trades
                current_value = len(pnl_report.items)

            elif goal.target_type == "roi":
                # Calculate overall ROI
                total_invested = sum(item.total_buy_value for item in pnl_report.items)
                if total_invested > 0:
                    current_value = (pnl_report.total_realized_pnl / total_invested) * 100

            # Update if changed
            if abs(current_value - goal.current_value) > 0.01:
                updated = self.update_goal_progress(goal.id, current_value)
                if updated:
                    # Recalculate progress
                    progress_percent = 0.0
                    if updated.target_value > 0:
                        progress_percent = min(100.0, (updated.current_value / updated.target_value) * 100)

                    goal_progress.goal = updated
                    goal_progress.progress_percent = round(progress_percent, 1)
                    goal_progress.remaining = max(0, updated.target_value - updated.current_value)

            updated_goals.append(goal_progress)

        return updated_goals
