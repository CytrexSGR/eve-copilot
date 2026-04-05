# mcp_tools/ai_plans_tools.py
"""
MCP Tools for AI Copilot plan management.
"""

import httpx
from typing import Optional, List

# Copilot server base URL
COPILOT_URL = "http://localhost:8002"


async def create_plan(
    character_id: int,
    title: str,
    goal_type: str,
    description: Optional[str] = None,
    target_data: Optional[dict] = None,
) -> dict:
    """
    Create a new plan for a character.

    Args:
        character_id: The character ID this plan belongs to
        title: Plan title (e.g., "Build a Golem")
        goal_type: Type of goal - 'ship', 'isk', 'skill', 'production', 'pi', 'custom'
        description: Optional detailed description
        target_data: Optional target parameters (e.g., {"ship_type_id": 28710})

    Returns:
        The created plan with ID
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COPILOT_URL}/agent/plans",
            json={
                "character_id": character_id,
                "title": title,
                "goal_type": goal_type,
                "description": description,
                "target_data": target_data or {},
            },
        )
        response.raise_for_status()
        return response.json()


async def get_active_plans(character_id: int, limit: int = 10) -> dict:
    """
    Get all active plans for a character.

    Args:
        character_id: The character ID to get plans for
        limit: Maximum number of plans to return

    Returns:
        List of active plans with milestones
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{COPILOT_URL}/agent/plans",
            params={"character_id": character_id, "status": "active", "limit": limit},
        )
        response.raise_for_status()
        return response.json()


async def get_plan(plan_id: int) -> dict:
    """
    Get a specific plan by ID with all milestones and resources.

    Args:
        plan_id: The plan ID

    Returns:
        Plan details with milestones and linked resources
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{COPILOT_URL}/agent/plans/{plan_id}")
        response.raise_for_status()
        return response.json()


async def update_plan_progress(plan_id: int, progress_pct: int) -> dict:
    """
    Update the progress percentage of a plan.

    Args:
        plan_id: The plan ID
        progress_pct: Progress percentage (0-100)

    Returns:
        Updated plan
    """
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{COPILOT_URL}/agent/plans/{plan_id}",
            json={"progress_pct": progress_pct},
        )
        response.raise_for_status()
        return response.json()


async def complete_plan(plan_id: int) -> dict:
    """
    Mark a plan as completed.

    Args:
        plan_id: The plan ID

    Returns:
        Updated plan with completed status
    """
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{COPILOT_URL}/agent/plans/{plan_id}",
            json={"status": "completed", "progress_pct": 100},
        )
        response.raise_for_status()
        return response.json()


async def add_milestone(
    plan_id: int,
    title: str,
    description: Optional[str] = None,
    tracking_type: Optional[str] = None,
    target_value: Optional[float] = None,
) -> dict:
    """
    Add a milestone to a plan.

    Args:
        plan_id: The plan ID
        title: Milestone title
        description: Optional description
        tracking_type: How to track progress - 'skill', 'wallet', 'shopping_list', 'ledger', 'manual'
        target_value: Target value for tracking (e.g., ISK amount, skill level)

    Returns:
        Created milestone
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COPILOT_URL}/agent/plans/{plan_id}/milestones",
            json={
                "title": title,
                "description": description,
                "tracking_type": tracking_type,
                "target_value": target_value,
            },
        )
        response.raise_for_status()
        return response.json()


async def update_milestone_progress(
    plan_id: int, milestone_id: int, current_value: float, status: Optional[str] = None
) -> dict:
    """
    Update milestone progress.

    Args:
        plan_id: The plan ID
        milestone_id: The milestone ID
        current_value: Current progress value
        status: Optional status update - 'pending', 'in_progress', 'completed', 'blocked'

    Returns:
        Updated milestone
    """
    data = {"current_value": current_value}
    if status:
        data["status"] = status

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{COPILOT_URL}/agent/plans/{plan_id}/milestones/{milestone_id}",
            json=data,
        )
        response.raise_for_status()
        return response.json()


async def link_resource_to_plan(
    plan_id: int, resource_type: str, resource_id: int
) -> dict:
    """
    Link a resource (shopping list, ledger, etc.) to a plan.

    Args:
        plan_id: The plan ID
        resource_type: Type of resource - 'shopping_list', 'ledger', 'pi_project', 'fitting'
        resource_id: The ID of the resource to link

    Returns:
        Resource link confirmation
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COPILOT_URL}/agent/plans/{plan_id}/resources",
            json={"resource_type": resource_type, "resource_id": resource_id},
        )
        response.raise_for_status()
        return response.json()


async def get_session_context(character_id: int) -> dict:
    """
    Get the context for starting a new session.
    Includes active plans and last session summary.

    Args:
        character_id: The character ID

    Returns:
        Context with active plans and previous session summary
    """
    context = {"character_id": character_id, "active_plans": [], "last_summary": None, "stored_context": []}

    async with httpx.AsyncClient() as client:
        # Get active plans
        try:
            response = await client.get(
                f"{COPILOT_URL}/agent/plans",
                params={"character_id": character_id, "status": "active"},
            )
            if response.status_code == 200:
                context["active_plans"] = response.json().get("plans", [])
        except Exception:
            pass

        # Get last session summary
        try:
            response = await client.get(f"{COPILOT_URL}/agent/session/restore/{character_id}")
            if response.status_code == 200:
                context["last_summary"] = response.json()
        except Exception:
            pass

        # Get stored context
        try:
            response = await client.get(f"{COPILOT_URL}/agent/context/{character_id}")
            if response.status_code == 200:
                context["stored_context"] = response.json().get("contexts", [])
        except Exception:
            pass

    return context


async def store_context(
    character_id: int, context_key: str, context_value: dict, source: str = "inferred"
) -> dict:
    """
    Store a piece of context about the character for future sessions.

    Args:
        character_id: The character ID
        context_key: Key for this context (e.g., "preferred_region", "trading_style")
        context_value: The value to store
        source: How this was learned - 'user_stated', 'inferred', 'system'

    Returns:
        Stored context confirmation
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COPILOT_URL}/agent/context/{character_id}",
            json={
                "context_key": context_key,
                "context_value": context_value,
                "source": source,
            },
        )
        response.raise_for_status()
        return response.json()


async def create_session_summary(
    session_id: str,
    character_id: int,
    summary: str,
    key_decisions: List[str] = None,
    open_questions: List[str] = None,
    active_plan_ids: List[int] = None,
) -> dict:
    """
    Create a summary of the current session for handoff to future sessions.

    Args:
        session_id: The current session ID
        character_id: The character ID
        summary: Text summary of what was discussed/accomplished
        key_decisions: List of key decisions made
        open_questions: List of unresolved questions
        active_plan_ids: IDs of plans that were active in this session

    Returns:
        Created summary
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COPILOT_URL}/agent/session/summarize",
            json={
                "session_id": session_id,
                "character_id": character_id,
                "summary": summary,
                "key_decisions": key_decisions or [],
                "open_questions": open_questions or [],
                "active_plan_ids": active_plan_ids or [],
            },
        )
        response.raise_for_status()
        return response.json()


# Tool definitions for MCP registration
AI_PLAN_TOOLS = [
    {
        "name": "create_plan",
        "description": "Create a new long-term plan or goal for a character. Use this when the user wants to track a multi-step objective like building a ship, reaching an ISK goal, or training skills.",
        "parameters": [
            {"name": "character_id", "type": "integer", "required": True, "description": "Character ID"},
            {"name": "title", "type": "string", "required": True, "description": "Plan title"},
            {"name": "goal_type", "type": "string", "required": True, "description": "Goal type: ship, isk, skill, production, pi, custom"},
            {"name": "description", "type": "string", "required": False, "description": "Detailed description"},
            {"name": "target_data", "type": "object", "required": False, "description": "Target parameters as JSON"},
        ],
        "function": create_plan,
    },
    {
        "name": "get_active_plans",
        "description": "Get all active plans for a character. Use this at the start of a session to see what the user is working on.",
        "parameters": [
            {"name": "character_id", "type": "integer", "required": True, "description": "Character ID"},
            {"name": "limit", "type": "integer", "required": False, "description": "Max plans to return (default 10)"},
        ],
        "function": get_active_plans,
    },
    {
        "name": "get_plan",
        "description": "Get details of a specific plan including all milestones and linked resources.",
        "parameters": [
            {"name": "plan_id", "type": "integer", "required": True, "description": "Plan ID"},
        ],
        "function": get_plan,
    },
    {
        "name": "update_plan_progress",
        "description": "Update the overall progress percentage of a plan.",
        "parameters": [
            {"name": "plan_id", "type": "integer", "required": True, "description": "Plan ID"},
            {"name": "progress_pct", "type": "integer", "required": True, "description": "Progress 0-100"},
        ],
        "function": update_plan_progress,
    },
    {
        "name": "complete_plan",
        "description": "Mark a plan as completed when all milestones are done.",
        "parameters": [
            {"name": "plan_id", "type": "integer", "required": True, "description": "Plan ID"},
        ],
        "function": complete_plan,
    },
    {
        "name": "add_milestone",
        "description": "Add a milestone (sub-goal) to an existing plan.",
        "parameters": [
            {"name": "plan_id", "type": "integer", "required": True, "description": "Plan ID"},
            {"name": "title", "type": "string", "required": True, "description": "Milestone title"},
            {"name": "description", "type": "string", "required": False, "description": "Description"},
            {"name": "tracking_type", "type": "string", "required": False, "description": "How to track: skill, wallet, shopping_list, ledger, manual"},
            {"name": "target_value", "type": "number", "required": False, "description": "Target value for tracking"},
        ],
        "function": add_milestone,
    },
    {
        "name": "update_milestone_progress",
        "description": "Update the progress of a specific milestone.",
        "parameters": [
            {"name": "plan_id", "type": "integer", "required": True, "description": "Plan ID"},
            {"name": "milestone_id", "type": "integer", "required": True, "description": "Milestone ID"},
            {"name": "current_value", "type": "number", "required": True, "description": "Current progress value"},
            {"name": "status", "type": "string", "required": False, "description": "Status: pending, in_progress, completed, blocked"},
        ],
        "function": update_milestone_progress,
    },
    {
        "name": "link_resource_to_plan",
        "description": "Link a shopping list, production ledger, or PI project to a plan for tracking.",
        "parameters": [
            {"name": "plan_id", "type": "integer", "required": True, "description": "Plan ID"},
            {"name": "resource_type", "type": "string", "required": True, "description": "Resource type: shopping_list, ledger, pi_project, fitting"},
            {"name": "resource_id", "type": "integer", "required": True, "description": "Resource ID"},
        ],
        "function": link_resource_to_plan,
    },
    {
        "name": "get_session_context",
        "description": "Get all context needed to start a new session: active plans, last session summary, and stored preferences. Call this at the beginning of each conversation.",
        "parameters": [
            {"name": "character_id", "type": "integer", "required": True, "description": "Character ID"},
        ],
        "function": get_session_context,
    },
    {
        "name": "store_context",
        "description": "Store a piece of information about the character for future sessions (preferences, patterns, learnings).",
        "parameters": [
            {"name": "character_id", "type": "integer", "required": True, "description": "Character ID"},
            {"name": "context_key", "type": "string", "required": True, "description": "Context key (e.g., preferred_region)"},
            {"name": "context_value", "type": "object", "required": True, "description": "Context value as JSON"},
            {"name": "source", "type": "string", "required": False, "description": "Source: user_stated, inferred, system"},
        ],
        "function": store_context,
    },
    {
        "name": "create_session_summary",
        "description": "Create a summary of the current session for handoff to future sessions. Call this before ending a conversation.",
        "parameters": [
            {"name": "session_id", "type": "string", "required": True, "description": "Current session ID"},
            {"name": "character_id", "type": "integer", "required": True, "description": "Character ID"},
            {"name": "summary", "type": "string", "required": True, "description": "Text summary of the session"},
            {"name": "key_decisions", "type": "array", "required": False, "description": "List of key decisions made"},
            {"name": "open_questions", "type": "array", "required": False, "description": "List of unresolved questions"},
            {"name": "active_plan_ids", "type": "array", "required": False, "description": "IDs of active plans"},
        ],
        "function": create_session_summary,
    },
]
