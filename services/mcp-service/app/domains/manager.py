"""Domain manager for dynamic tool registry and activation."""

from typing import Dict, List, Optional
import logging
from ..openapi.parser import OpenAPIParser
from ..openapi.converter import endpoint_to_mcp_tool

logger = logging.getLogger(__name__)


class DomainManager:
    """
    Manages domain activation and dynamic tool registry.

    Responsibilities:
        - Load OpenAPI specs at startup
        - Store parsed tools per domain
        - Track active domain state
        - Provide domain switcher tools
        - Return tools for active domain
    """

    # Service definitions: domain_name -> OpenAPI spec URL
    SERVICES = {
        'market': 'http://market-service:8000/openapi.json',
        'war_intel': 'http://war-intel-service:8000/openapi.json',
        'production': 'http://production-service:8000/openapi.json',
        'shopping': 'http://shopping-service:8000/openapi.json',
        'character': 'http://character-service:8000/openapi.json',
        'auth': 'http://auth-service:8000/openapi.json',
        'scheduler': 'http://scheduler-service:8000/openapi.json',
        'wormhole': 'http://wormhole-service:8000/openapi.json',
    }

    def __init__(self):
        """Initialize domain manager."""
        self.parser = OpenAPIParser()
        self.active_domain: Optional[str] = None
        self.domain_tools: Dict[str, List[dict]] = {}

    async def initialize(self):
        """Load all OpenAPI specs at startup and convert to MCP tools."""
        logger.info("Initializing domain manager...")

        for service_name, spec_url in self.SERVICES.items():
            try:
                # Fetch OpenAPI spec
                await self.parser.load_service_spec(service_name, spec_url)

                # Parse endpoints (MCP-only for war_intel)
                mcp_only = (service_name == 'war_intel')
                endpoints = self.parser.parse_endpoints(service_name, mcp_only=mcp_only)

                # Convert to MCP tools
                self.domain_tools[service_name] = [
                    endpoint_to_mcp_tool(ep) for ep in endpoints
                ]

                logger.info(f"✅ Loaded {len(endpoints)} endpoints from {service_name} (mcp_only={mcp_only})")

            except Exception as e:
                logger.error(f"❌ Failed to load {service_name}: {e}")
                self.domain_tools[service_name] = []

        total_tools = sum(len(tools) for tools in self.domain_tools.values())
        logger.info(f"Domain manager initialized with {total_tools} total dynamic tools")

    async def enable_domain(self, domain: str) -> dict:
        """
        Activate a domain (e.g., 'market').

        Args:
            domain: Domain identifier

        Returns:
            Success message with tool count
        """
        if domain not in self.SERVICES:
            available = list(self.SERVICES.keys())
            logger.warning(f"Domain '{domain}' not found. Available: {available}")
            return {
                'success': False,
                'message': f"Domain '{domain}' not found. Available: {available}"
            }

        self.active_domain = domain
        domain_tools_list = self.domain_tools.get(domain, [])
        tool_count = len(domain_tools_list)

        logger.info(f"Domain '{domain}' enabled with {tool_count} tools")

        # Show first 20 tools as examples
        tool_names = [t['name'] for t in domain_tools_list[:20]]
        tool_preview = '\n'.join([f"  • {name}" for name in tool_names])
        if tool_count > 20:
            tool_preview += f"\n  ... and {tool_count - 20} more tools"

        domain_name = domain.replace('_', ' ').title()

        return {
            'success': True,
            'domain': domain,
            'tool_count': tool_count,
            'message': f"""✅ {domain_name} domain enabled with {tool_count} tools!

📋 AVAILABLE TOOLS (showing first 20):
{tool_preview}

💡 TIP: All tools are now in your tools/list. Just call them by name!

🔄 TO SWITCH DOMAINS: Call another enable_X_tools (e.g., enable_market_tools)
   The domain switchers are hidden while a domain is active, but you can
   still call them to switch domains."""
        }

    def get_active_tools(self) -> List[dict]:
        """
        Return tools for active domain.

        If no domain is active, returns domain switcher tools.
        If domain is active, returns that domain's tools.

        Returns:
            List of MCP tool definitions
        """
        if not self.active_domain:
            return self._get_domain_switchers()

        return self.domain_tools.get(self.active_domain, [])

    def _get_domain_switchers(self) -> List[dict]:
        """
        Generate top-level tools for domain activation.

        Returns one tool per domain:
            - enable_market_tools()
            - enable_war_intel_tools() (future)
            - etc.

        Returns:
            List of domain switcher tool definitions
        """
        switchers = []

        for domain in self.SERVICES.keys():
            tool_count = len(self.domain_tools.get(domain, []))
            domain_title = domain.replace('_', ' ').title()

            # Custom descriptions for specific domains
            if domain == 'war_intel':
                description = (
                    f'Enable War Intelligence API tools ({tool_count} endpoints). '
                    'Analyze Corporations, Alliances, Power Blocs, Battles, System Danger, '
                    'Sovereignty, Jump Routes, Structure Timers, Market Intel. '
                    'For Corporation research, use this domain.'
                )
            else:
                description = (
                    f'Enable {domain_title} API tools. '
                    f'Provides access to {tool_count} {domain} service endpoints.'
                )

            switchers.append({
                'name': f'enable_{domain}_tools',
                'description': description,
                'inputSchema': {
                    'type': 'object',
                    'properties': {},
                    'required': []
                },
                '_domain_switch': domain
            })

        return switchers
