"""
MCP Tools Router
Model Context Protocol implementation for EVE Co-Pilot.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List
import traceback
import logging

from app.services.tool_registry import tool_registry

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# Request/Response Models
class ToolCallRequest(BaseModel):
    """Request model for MCP tool calls."""
    name: str
    arguments: Dict[str, Any] = {}


class ToolListResponse(BaseModel):
    """Response model for tool listing."""
    tools: List[Dict[str, Any]]
    count: int
    categories: Dict[str, int]


# Routes
@router.get("/tools/list", response_model=ToolListResponse)
def list_tools():
    """
    List all available MCP tools.

    Returns:
        List of tool definitions with metadata
    """
    tools = tool_registry.get_all_tools()
    counts = tool_registry.get_tool_counts()

    return {
        "tools": tools,
        "count": len(tools),
        "categories": counts
    }


@router.post("/tools/call")
async def call_tool(request: ToolCallRequest):
    """
    Execute an MCP tool.

    Args:
        request: Tool call request with name and arguments

    Returns:
        Tool execution result in MCP format
    """
    tool_name = request.name
    args = request.arguments

    # Get handler
    handler = tool_registry.get_handler(tool_name)
    if not handler:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found. Use /mcp/tools/list to see available tools."
        )

    # Execute handler
    try:
        result = await handler(args)
        return result
    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"Tool '{tool_name}' execution failed: {error_msg}")
        return {
            "error": error_msg,
            "isError": True
        }


# =============================================================================
# Dynamic OpenAPI-based Tools (must be before parametrized routes!)
# =============================================================================

@router.get("/tools/list-dynamic")
def list_dynamic_tools():
    """
    List dynamic tools for active domain.

    Returns tools based on current domain state:
    - If no domain is active: returns domain switcher tools
    - If domain is active: returns that domain's tools

    Returns:
        List of dynamic tool definitions with active domain info
    """
    # Import here to avoid circular dependency
    from app import main

    tools = main.domain_manager.get_active_tools()

    return {
        "tools": tools,
        "count": len(tools),
        "active_domain": main.domain_manager.active_domain
    }


@router.post("/tools/call-dynamic")
async def call_dynamic_tool(request: ToolCallRequest):
    """
    Execute dynamic tools (generated from OpenAPI).

    Workflow:
        1. Find tool in active domain's tool list
        2. Check if it's a domain switcher → enable domain
        3. Otherwise → extract metadata → call API endpoint

    Args:
        request: Tool call request with name and arguments

    Returns:
        Tool execution result in MCP format
    """
    # Import here to avoid circular dependency
    from app import main

    tool_name = request.name
    arguments = request.arguments

    # Find tool in active domain
    active_tools = main.domain_manager.get_active_tools()
    tool = next((t for t in active_tools if t['name'] == tool_name), None)

    if not tool:
        return {
            "error": f"Tool '{tool_name}' not found",
            "isError": True
        }

    # Is it a domain switcher?
    if '_domain_switch' in tool:
        result = await main.domain_manager.enable_domain(tool['_domain_switch'])
        return {
            "content": [{"type": "text", "text": str(result)}]
        }

    # Extract metadata for API call
    metadata = tool.get('_metadata')
    if not metadata:
        return {
            "error": "Tool missing metadata",
            "isError": True
        }

    # Execute API call
    try:
        result = await main.api_handler.call_endpoint(
            service=metadata['service'],
            method=metadata['method'],
            path=metadata['path'],
            arguments=arguments
        )

        return {
            "content": [{"type": "text", "text": str(result)}]
        }

    except Exception as e:
        error_msg = f"Dynamic tool execution failed: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"Tool '{tool_name}' execution failed: {error_msg}")
        return {
            "error": str(e),
            "isError": True
        }


# =============================================================================
# Static Tool Info Routes (must be after dynamic routes!)
# =============================================================================

@router.get("/tools/{tool_name}")
def get_tool_info(tool_name: str):
    """
    Get information about a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool definition
    """
    tool = tool_registry.get_tool(tool_name)
    if not tool:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found"
        )

    return tool


@router.get("/health")
def health_check():
    """MCP server health check."""
    tools = tool_registry.get_all_tools()
    counts = tool_registry.get_tool_counts()

    return {
        "status": "healthy",
        "total_tools": len(tools),
        "categories": counts
    }
