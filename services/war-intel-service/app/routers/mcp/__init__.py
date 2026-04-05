"""
MCP (Model Context Protocol) Router for War-Intel Service.

Provides 12 AI-agent-friendly tools combining multiple frontend endpoints
into flexible, parameter-driven operations.

Tool Categories:
- Alliance Intelligence (3 tools): analyze, threats, readiness
- Corporation Intelligence (1 tool): analyze corporation
- Power Bloc Intelligence (2 tools): list all blocs, analyze bloc
- Battle Intelligence (2 tools): find battles, analyze battle
- Strategic (3 tools): threat assessment, conflicts, sovereignty
- Operations (2 tools): jump routes, structure timers
- Economy (2 tools): market intel, mining ops
"""

from fastapi import APIRouter
from . import alliance, corporation, powerblocs, battles, strategic, operations, economy

mcp_router = APIRouter()

# Include all MCP sub-routers
mcp_router.include_router(alliance.router, tags=["MCP - Alliance"])
mcp_router.include_router(corporation.router, tags=["MCP - Corporation"])
mcp_router.include_router(powerblocs.router, tags=["MCP - Power Blocs"])
mcp_router.include_router(battles.router, tags=["MCP - Battles"])
mcp_router.include_router(strategic.router, tags=["MCP - Strategic"])
mcp_router.include_router(operations.router, tags=["MCP - Operations"])
mcp_router.include_router(economy.router, tags=["MCP - Economy"])
