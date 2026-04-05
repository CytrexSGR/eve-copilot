"""
MCP Tool Registry
Centralized registry of all MCP tool definitions and handlers.
Tools call other microservices via HTTP for execution.
"""

import httpx
import logging
import traceback
from typing import Any, Callable, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class ServiceProxy:
    """Helper class for proxying MCP tool calls to microservice endpoints."""

    def __init__(self):
        self.timeout = settings.tool_timeout_seconds

        # Service URL routing
        self.service_routes = {
            # Auth service (8001)
            "/api/auth": settings.auth_service_url,
            "/api/settings": settings.auth_service_url,

            # War Intel service (8002)
            "/api/war": settings.war_intel_service_url,
            "/api/dps": settings.war_intel_service_url,
            "/api/risk": settings.war_intel_service_url,
            "/api/reports": settings.war_intel_service_url,

            # Scheduler service (8003)
            "/api/scheduler": settings.scheduler_service_url,
            "/api/jobs": settings.scheduler_service_url,

            # Market service (8004)
            "/api/market": settings.market_service_url,
            "/api/hunter": settings.market_service_url,
            "/api/trading": settings.market_service_url,
            "/api/alerts": settings.market_service_url,
            "/api/goals": settings.market_service_url,
            "/api/history": settings.market_service_url,
            "/api/bookmarks": settings.market_service_url,
            "/api/portfolio": settings.market_service_url,
            "/api/items": settings.market_service_url,
            "/api/materials": settings.market_service_url,
            "/api/route": settings.market_service_url,

            # Production service (8005)
            "/api/production": settings.production_service_url,
            "/api/pi": settings.production_service_url,
            "/api/mining": settings.production_service_url,
            "/api/supply-chain": settings.production_service_url,
            "/api/reactions": settings.production_service_url,

            # Shopping service (8006)
            "/api/shopping": settings.shopping_service_url,

            # Character service (8007)
            "/api/character": settings.character_service_url,
            "/api/fittings": settings.character_service_url,
            "/api/mastery": settings.character_service_url,
            "/api/skills": settings.character_service_url,
            "/api/research": settings.character_service_url,

            # Wormhole service (8012)
            "/api/wormhole": settings.wormhole_service_url,

            # DOTLAN service (8014)
            "/api/dotlan": settings.dotlan_service_url,

            # HR service (8015)
            "/api/hr": settings.hr_service_url,

            # Finance service (8016)
            "/api/finance": settings.finance_service_url,
            "/api/srp": settings.finance_service_url,
            "/api/doctrine": settings.finance_service_url,
            "/api/buyback": settings.finance_service_url,

            # Military service (8020)
            "/api/military": settings.military_service_url,

            # ZKillboard service (8013)
            "/api/zkillboard": settings.zkillboard_service_url,

            # ECTMap service (8011)
            "/ectmap": settings.ectmap_service_url,
        }

    def _get_service_url(self, endpoint: str) -> str:
        """Route endpoint to appropriate service."""
        for prefix, base_url in self.service_routes.items():
            if endpoint.startswith(prefix):
                return base_url
        # Default to monolith for unrouted endpoints
        return settings.monolith_url

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make GET request to appropriate service endpoint.

        Args:
            endpoint: API endpoint path (e.g., "/api/market/stats/10000002/34")
            params: Optional query parameters

        Returns:
            API response as dict with {"content": [...]} or {"error": "..."}
        """
        try:
            base_url = self._get_service_url(endpoint)
            url = f"{base_url}{endpoint}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                return {"content": [{"type": "text", "text": str(data)}]}

        except httpx.HTTPStatusError as e:
            error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            return {"error": error_msg, "isError": True}
        except httpx.RequestError as e:
            error_msg = f"API request failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "isError": True}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {"error": error_msg, "isError": True}

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make POST request to appropriate service endpoint.

        Args:
            endpoint: API endpoint path
            data: Optional request body
            params: Optional query parameters

        Returns:
            API response as dict with {"content": [...]} or {"error": "..."}
        """
        try:
            base_url = self._get_service_url(endpoint)
            url = f"{base_url}{endpoint}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=data, params=params)
                response.raise_for_status()

                result = response.json()
                return {"content": [{"type": "text", "text": str(result)}]}

        except httpx.HTTPStatusError as e:
            error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            return {"error": error_msg, "isError": True}
        except httpx.RequestError as e:
            error_msg = f"API request failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "isError": True}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {"error": error_msg, "isError": True}

    async def patch(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make PATCH request to appropriate service endpoint.

        Args:
            endpoint: API endpoint path
            data: Optional request body

        Returns:
            API response as dict with {"content": [...]} or {"error": "..."}
        """
        try:
            base_url = self._get_service_url(endpoint)
            url = f"{base_url}{endpoint}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.patch(url, json=data)
                response.raise_for_status()

                result = response.json()
                return {"content": [{"type": "text", "text": str(result)}]}

        except httpx.HTTPStatusError as e:
            error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            return {"error": error_msg, "isError": True}
        except httpx.RequestError as e:
            error_msg = f"API request failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "isError": True}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {"error": error_msg, "isError": True}

    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """
        Make DELETE request to appropriate service endpoint.

        Args:
            endpoint: API endpoint path

        Returns:
            API response as dict with {"content": [...]} or {"error": "..."}
        """
        try:
            base_url = self._get_service_url(endpoint)
            url = f"{base_url}{endpoint}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(url)
                response.raise_for_status()

                result = response.json()
                return {"content": [{"type": "text", "text": str(result)}]}

        except httpx.HTTPStatusError as e:
            error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            return {"error": error_msg, "isError": True}
        except httpx.RequestError as e:
            error_msg = f"API request failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "isError": True}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {"error": error_msg, "isError": True}


# Global service proxy instance
service_proxy = ServiceProxy()


class ToolRegistry:
    """
    Central registry for MCP tools.
    Tools are defined here with their metadata and handlers.
    Handlers proxy requests to appropriate microservices.
    """

    def __init__(self):
        self._tools: List[Dict[str, Any]] = []
        self._handlers: Dict[str, Callable] = {}
        self._categories: Dict[str, int] = {}

        # Register all tools on initialization
        self._register_all_tools()

    def _register_all_tools(self):
        """Register all available MCP tools."""
        # Context tools
        self._register_context_tools()

        # Character tools
        self._register_character_tools()

        # Market tools
        self._register_market_tools()

        # Production tools
        self._register_production_tools()

        # War Room tools
        self._register_war_room_tools()

        # Shopping tools
        self._register_shopping_tools()

        # Calculate category counts
        self._update_category_counts()

    def _update_category_counts(self):
        """Update tool counts by category."""
        counts = {}
        for tool in self._tools:
            category = tool.get("category", "other")
            counts[category] = counts.get(category, 0) + 1
        counts["total"] = len(self._tools)
        self._categories = counts

    def _register_tool(
        self,
        name: str,
        description: str,
        category: str,
        handler: Callable,
        parameters: Optional[List[Dict[str, Any]]] = None
    ):
        """Register a single tool."""
        tool = {
            "name": name,
            "description": description,
            "category": category,
            "parameters": parameters or []
        }
        self._tools.append(tool)
        self._handlers[name] = handler

    # ========== Context Tools ==========
    def _register_context_tools(self):
        """Register context and utility tools."""

        async def handle_get_regions(args: Dict[str, Any]) -> Dict[str, Any]:
            """Get all EVE Online regions."""
            return await service_proxy.get("/api/regions")

        async def handle_eve_copilot_context(args: Dict[str, Any]) -> Dict[str, Any]:
            """Get EVE Co-Pilot system context."""
            try:
                # Get authenticated characters from auth service
                result = await service_proxy.get("/api/auth/characters")

                context = {
                    "system": "EVE Co-Pilot",
                    "version": "2.0.0",
                    "capabilities": [
                        "Market Analysis & Arbitrage Finding",
                        "Production Planning & Cost Calculation",
                        "Shopping List Management with Regional Comparison",
                        "War Room - Combat Intelligence & Demand Analysis",
                        "Character & Corporation Management",
                        "Research & Skill Planning",
                        "Route Calculation & Navigation",
                        "Mining Location Finder",
                        "Bookmark Management"
                    ],
                    "mcp_tools": len(self._tools),
                    "tips": [
                        "Use get_regions to see available regions for market queries",
                        "War Room tools require region_id (e.g., 10000002 for Jita/The Forge)",
                        "Shopping wizard guides you through creating optimized shopping lists",
                        "Production chains show full material breakdown from raw materials"
                    ]
                }

                return {"content": [{"type": "text", "text": str(context)}]}
            except Exception as e:
                return {"error": f"Failed to get context: {str(e)}", "isError": True}

        self._register_tool(
            "get_regions",
            "Get list of all EVE Online regions with their IDs.",
            "context",
            handle_get_regions,
            [
                {
                    "name": "include_wh",
                    "type": "boolean",
                    "required": False,
                    "description": "Include wormhole regions (default: false)",
                    "default": False
                }
            ]
        )

        self._register_tool(
            "eve_copilot_context",
            "Get EVE Co-Pilot system context and capabilities.",
            "context",
            handle_eve_copilot_context
        )

    # ========== Character Tools ==========
    def _register_character_tools(self):
        """Register character-related tools."""

        async def handle_get_characters(args: Dict[str, Any]) -> Dict[str, Any]:
            """Get authenticated characters."""
            return await service_proxy.get("/api/auth/characters")

        async def handle_get_character_wallet(args: Dict[str, Any]) -> Dict[str, Any]:
            """Get character wallet balance."""
            char_id = args.get("character_id")
            if not char_id:
                return {"error": "character_id is required", "isError": True}
            return await service_proxy.get(f"/api/character/{char_id}/wallet")

        async def handle_get_character_skills(args: Dict[str, Any]) -> Dict[str, Any]:
            """Get character skills."""
            char_id = args.get("character_id")
            if not char_id:
                return {"error": "character_id is required", "isError": True}
            return await service_proxy.get(f"/api/character/{char_id}/skills")

        async def handle_get_character_assets(args: Dict[str, Any]) -> Dict[str, Any]:
            """Get character assets."""
            char_id = args.get("character_id")
            if not char_id:
                return {"error": "character_id is required", "isError": True}
            return await service_proxy.get(f"/api/character/{char_id}/assets")

        async def handle_get_ship_mastery(args: Dict[str, Any]) -> Dict[str, Any]:
            """Get ship mastery level for a character."""
            char_id = args.get("character_id")
            ship_id = args.get("ship_type_id")
            if not char_id or not ship_id:
                return {"error": "character_id and ship_type_id are required", "isError": True}
            return await service_proxy.get(
                f"/api/mastery/character/{char_id}/ship/{ship_id}"
            )

        self._register_tool(
            "get_characters",
            "Get list of authenticated EVE Online characters.",
            "character",
            handle_get_characters
        )

        self._register_tool(
            "get_character_wallet",
            "Get character wallet balance.",
            "character",
            handle_get_character_wallet,
            [{"name": "character_id", "type": "integer", "required": True}]
        )

        self._register_tool(
            "get_character_skills",
            "Get character skills and skill points.",
            "character",
            handle_get_character_skills,
            [{"name": "character_id", "type": "integer", "required": True}]
        )

        self._register_tool(
            "get_character_assets",
            "Get character assets and inventory.",
            "character",
            handle_get_character_assets,
            [{"name": "character_id", "type": "integer", "required": True}]
        )

        self._register_tool(
            "get_ship_mastery",
            "Get ship mastery level (0-4) for a character.",
            "mastery",
            handle_get_ship_mastery,
            [
                {"name": "character_id", "type": "integer", "required": True},
                {"name": "ship_type_id", "type": "integer", "required": True}
            ]
        )

    # ========== Market Tools ==========
    def _register_market_tools(self):
        """Register market-related tools."""

        async def handle_get_market_stats(args: Dict[str, Any]) -> Dict[str, Any]:
            """Get market statistics for an item in a region."""
            region_id = args.get("region_id", 10000002)  # Default to The Forge (Jita)
            type_id = args.get("type_id")
            if not type_id:
                return {"error": "type_id is required", "isError": True}
            return await service_proxy.get(f"/api/market/stats/{region_id}/{type_id}")

        async def handle_compare_market_prices(args: Dict[str, Any]) -> Dict[str, Any]:
            """Compare prices across multiple regions."""
            type_id = args.get("type_id")
            if not type_id:
                return {"error": "type_id is required", "isError": True}
            return await service_proxy.get(f"/api/market/compare/{type_id}")

        async def handle_find_arbitrage(args: Dict[str, Any]) -> Dict[str, Any]:
            """Find arbitrage opportunities for an item."""
            type_id = args.get("type_id")
            if not type_id:
                return {"error": "type_id is required", "isError": True}
            return await service_proxy.get(f"/api/market/arbitrage/{type_id}")

        async def handle_search_items(args: Dict[str, Any]) -> Dict[str, Any]:
            """Search for items by name."""
            query = args.get("query")
            if not query:
                return {"error": "query is required", "isError": True}
            return await service_proxy.get("/api/items/search", params={"q": query})

        self._register_tool(
            "get_market_stats",
            "Get market statistics (price, volume, orders) for an item in a region.",
            "market",
            handle_get_market_stats,
            [
                {"name": "type_id", "type": "integer", "required": True},
                {"name": "region_id", "type": "integer", "required": False, "default": 10000002}
            ]
        )

        self._register_tool(
            "compare_market_prices",
            "Compare market prices across all major trade hubs.",
            "market",
            handle_compare_market_prices,
            [{"name": "type_id", "type": "integer", "required": True}]
        )

        self._register_tool(
            "find_arbitrage",
            "Find arbitrage opportunities for an item between regions.",
            "market",
            handle_find_arbitrage,
            [{"name": "type_id", "type": "integer", "required": True}]
        )

        self._register_tool(
            "search_items",
            "Search for EVE items by name.",
            "items",
            handle_search_items,
            [{"name": "query", "type": "string", "required": True}]
        )

    # ========== Production Tools ==========
    def _register_production_tools(self):
        """Register production-related tools."""

        async def handle_get_production_cost(args: Dict[str, Any]) -> Dict[str, Any]:
            """Calculate production cost for an item."""
            type_id = args.get("type_id")
            me = args.get("me", 10)
            if not type_id:
                return {"error": "type_id is required", "isError": True}
            return await service_proxy.get(
                f"/api/production/cost/{type_id}",
                params={"me": me}
            )

        async def handle_get_production_chain(args: Dict[str, Any]) -> Dict[str, Any]:
            """Get full production chain for an item."""
            type_id = args.get("type_id")
            if not type_id:
                return {"error": "type_id is required", "isError": True}
            return await service_proxy.get(f"/api/production/chains/{type_id}")

        async def handle_optimize_production(args: Dict[str, Any]) -> Dict[str, Any]:
            """Find optimal production location across regions."""
            type_id = args.get("type_id")
            me = args.get("me", 10)
            if not type_id:
                return {"error": "type_id is required", "isError": True}
            return await service_proxy.get(
                f"/api/production/optimize/{type_id}",
                params={"me": me}
            )

        self._register_tool(
            "get_production_cost",
            "Calculate production cost for an item with material efficiency.",
            "production",
            handle_get_production_cost,
            [
                {"name": "type_id", "type": "integer", "required": True},
                {"name": "me", "type": "integer", "required": False, "default": 10}
            ]
        )

        self._register_tool(
            "get_production_chain",
            "Get full production chain showing all required materials.",
            "production",
            handle_get_production_chain,
            [{"name": "type_id", "type": "integer", "required": True}]
        )

        self._register_tool(
            "optimize_production",
            "Find optimal production location across regions.",
            "production",
            handle_optimize_production,
            [
                {"name": "type_id", "type": "integer", "required": True},
                {"name": "me", "type": "integer", "required": False, "default": 10}
            ]
        )

    # ========== War Room Tools ==========
    def _register_war_room_tools(self):
        """Register war room and combat intelligence tools."""

        async def handle_get_combat_losses(args: Dict[str, Any]) -> Dict[str, Any]:
            """Get combat losses for a region."""
            region_id = args.get("region_id")
            days = args.get("days", 7)
            if not region_id:
                return {"error": "region_id is required", "isError": True}
            return await service_proxy.get(
                f"/api/war/losses/{region_id}",
                params={"days": days}
            )

        async def handle_get_active_battles(args: Dict[str, Any]) -> Dict[str, Any]:
            """Get active battles in progress."""
            limit = args.get("limit", 100)
            return await service_proxy.get(
                "/api/war/battles/active",
                params={"limit": limit}
            )

        async def handle_get_system_danger(args: Dict[str, Any]) -> Dict[str, Any]:
            """Get danger score for a solar system."""
            system_id = args.get("system_id")
            if not system_id:
                return {"error": "system_id is required", "isError": True}
            return await service_proxy.get(f"/api/war/system/{system_id}/danger")

        self._register_tool(
            "get_combat_losses",
            "Get combat ship and module losses for a region.",
            "war_room",
            handle_get_combat_losses,
            [
                {"name": "region_id", "type": "integer", "required": True},
                {"name": "days", "type": "integer", "required": False, "default": 7}
            ]
        )

        self._register_tool(
            "get_active_battles",
            "Get currently active battles across New Eden.",
            "war_room",
            handle_get_active_battles,
            [{"name": "limit", "type": "integer", "required": False, "default": 100}]
        )

        self._register_tool(
            "get_system_danger",
            "Get danger score and recent kills for a solar system.",
            "war_room",
            handle_get_system_danger,
            [{"name": "system_id", "type": "integer", "required": True}]
        )

    # ========== Shopping Tools ==========
    def _register_shopping_tools(self):
        """Register shopping list tools."""

        async def handle_get_shopping_lists(args: Dict[str, Any]) -> Dict[str, Any]:
            """Get all shopping lists."""
            return await service_proxy.get("/api/shopping/lists")

        async def handle_create_shopping_list(args: Dict[str, Any]) -> Dict[str, Any]:
            """Create a new shopping list."""
            name = args.get("name")
            if not name:
                return {"error": "name is required", "isError": True}
            return await service_proxy.post(
                "/api/shopping/lists",
                data={"name": name, "description": args.get("description", "")}
            )

        async def handle_add_to_shopping_list(args: Dict[str, Any]) -> Dict[str, Any]:
            """Add an item to a shopping list."""
            list_id = args.get("list_id")
            type_id = args.get("type_id")
            quantity = args.get("quantity", 1)
            if not list_id or not type_id:
                return {"error": "list_id and type_id are required", "isError": True}
            return await service_proxy.post(
                f"/api/shopping/lists/{list_id}/items",
                data={"type_id": type_id, "quantity": quantity}
            )

        self._register_tool(
            "get_shopping_lists",
            "Get all shopping lists.",
            "shopping",
            handle_get_shopping_lists
        )

        self._register_tool(
            "create_shopping_list",
            "Create a new shopping list.",
            "shopping",
            handle_create_shopping_list,
            [
                {"name": "name", "type": "string", "required": True},
                {"name": "description", "type": "string", "required": False}
            ]
        )

        self._register_tool(
            "add_to_shopping_list",
            "Add an item to a shopping list.",
            "shopping",
            handle_add_to_shopping_list,
            [
                {"name": "list_id", "type": "integer", "required": True},
                {"name": "type_id", "type": "integer", "required": True},
                {"name": "quantity", "type": "integer", "required": False, "default": 1}
            ]
        )

    # ========== Public API ==========
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all registered tools."""
        return self._tools

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool by name."""
        for tool in self._tools:
            if tool["name"] == name:
                return tool
        return None

    def get_handler(self, name: str) -> Optional[Callable]:
        """Get handler function for a tool."""
        return self._handlers.get(name)

    def get_tool_counts(self) -> Dict[str, int]:
        """Get tool counts by category."""
        return self._categories


# Global registry instance
tool_registry = ToolRegistry()
