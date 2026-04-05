"""
MCP SSE Bridge for EVE Co-Pilot.

Exposes the existing tool_registry and ALL dynamic domain tools
via standard MCP SSE transport for mcporter/OpenClaw integration.
All tools from all 13 services are available simultaneously.
"""

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

# Create MCP server instance
mcp_server = Server("eve-copilot")

# SSE transport
sse_transport = SseServerTransport("/sse/messages/")


def _convert_params_to_json_schema(params: list[dict]) -> dict:
    """Convert tool_registry parameter format to JSON Schema."""
    if not params:
        return {"type": "object", "properties": {}, "required": []}

    properties = {}
    required = []

    type_map = {
        "integer": "integer", "int": "integer",
        "string": "string", "str": "string",
        "boolean": "boolean", "bool": "boolean",
        "number": "number", "float": "number",
    }

    for param in params:
        name = param["name"]
        prop: dict[str, Any] = {
            "type": type_map.get(param.get("type", "string"), "string"),
        }
        if "description" in param:
            prop["description"] = param["description"]
        if "default" in param:
            prop["default"] = param["default"]
        properties[name] = prop
        if param.get("required", False):
            required.append(name)

    return {"type": "object", "properties": properties, "required": required}


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List ALL available tools: static + all dynamic from all domains + call_eve_api."""
    tools: list[Tool] = []
    seen_names: set[str] = set()

    # 1) Static tools from tool_registry
    from app.services.tool_registry import tool_registry
    for tool_def in tool_registry.get_all_tools():
        schema = _convert_params_to_json_schema(tool_def.get("parameters", []))
        tools.append(Tool(
            name=tool_def["name"],
            description=tool_def.get("description", ""),
            inputSchema=schema,
        ))
        seen_names.add(tool_def["name"])

    # 2) ALL dynamic tools from ALL domains (no switching)
    from app.main import domain_manager
    all_domain_tools = domain_manager.get_all_domain_tools()
    for dt in all_domain_tools:
        if dt["name"] in seen_names:
            continue
        tools.append(Tool(
            name=dt["name"],
            description=dt.get("description", ""),
            inputSchema=dt.get("inputSchema", {
                "type": "object", "properties": {}, "required": []
            }),
        ))
        seen_names.add(dt["name"])

    # 3) Meta-tool: call any EVE API endpoint
    tools.append(Tool(
        name="call_eve_api",
        description=(
            "Call any EVE Co-Pilot API endpoint directly. "
            "Use when no specific tool exists. Supports GET, POST, PATCH, DELETE. "
            "Available prefixes: /api/auth, /api/character, /api/market, "
            "/api/production, /api/war, /api/wormhole, /api/hr, /api/finance, "
            "/api/shopping, /api/fittings, /api/sovereignty, /api/dotlan, "
            "/api/intelligence, /api/powerbloc, /api/alliances, /api/military, /ectmap, "
            "/api/srp, /api/doctrine, /api/mining, /api/pi, /api/reactions"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "description": "HTTP method (GET, POST, PATCH, DELETE)",
                    "default": "GET",
                },
                "endpoint": {
                    "type": "string",
                    "description": "API path, e.g. /api/market/stats/10000002/34",
                },
                "params": {
                    "type": "object",
                    "description": "Query parameters (GET) or JSON body (POST/PATCH)",
                    "default": {},
                },
            },
            "required": ["endpoint"],
        },
    ))

    logger.info(f"MCP SSE: listing {len(tools)} tools ({len(all_domain_tools)} dynamic + {len(tool_registry.get_all_tools())} static + 1 meta)")
    return tools


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Dispatch tool calls to the appropriate handler."""
    from app.services.tool_registry import tool_registry, service_proxy
    from app.main import domain_manager, api_handler

    # 1) Meta-tool: call_eve_api
    if name == "call_eve_api":
        method = arguments.get("method", "GET").upper()
        endpoint = arguments.get("endpoint", "")
        params = arguments.get("params", {})

        if not endpoint:
            return [TextContent(type="text", text='{"error": "endpoint is required"}')]

        try:
            if method == "GET":
                result = await service_proxy.get(endpoint, params=params or None)
            elif method == "POST":
                result = await service_proxy.post(endpoint, data=params or None)
            elif method == "PATCH":
                result = await service_proxy.patch(endpoint, data=params or None)
            elif method == "DELETE":
                result = await service_proxy.delete(endpoint)
            else:
                result = {"error": f"Unsupported method: {method}"}
        except Exception as e:
            result = {"error": str(e)}

        if isinstance(result, dict) and "content" in result:
            text = result["content"][0].get("text", json.dumps(result))
        else:
            text = json.dumps(result)
        return [TextContent(type="text", text=text)]

    # 2) Static tool from tool_registry
    handler = tool_registry.get_handler(name)
    if handler:
        result = await handler(arguments)
        if isinstance(result, dict):
            if "content" in result and isinstance(result["content"], list):
                text = result["content"][0].get("text", json.dumps(result))
            elif "error" in result:
                text = json.dumps({"error": result["error"]})
            else:
                text = json.dumps(result)
        else:
            text = str(result)
        return [TextContent(type="text", text=text)]

    # 3) Dynamic tool from any domain
    all_tools = domain_manager.get_all_domain_tools()
    tool = next((t for t in all_tools if t["name"] == name), None)

    if tool:
        metadata = tool.get("_metadata")
        if metadata:
            try:
                result = await api_handler.call_endpoint(
                    service=metadata["service"],
                    method=metadata["method"],
                    path=metadata["path"],
                    arguments=arguments,
                )
                return [TextContent(type="text", text=json.dumps(result) if isinstance(result, dict) else str(result))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    return [TextContent(type="text", text=json.dumps({"error": f"Tool '{name}' not found"}))]
