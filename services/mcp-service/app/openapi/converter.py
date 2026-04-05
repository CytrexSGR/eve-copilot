"""Convert OpenAPI endpoints to MCP Tool format."""

from typing import Dict, Any
from .parser import OpenAPIEndpoint
import logging

logger = logging.getLogger(__name__)


def endpoint_to_mcp_tool(endpoint: OpenAPIEndpoint) -> Dict[str, Any]:
    """
    Convert OpenAPI endpoint to MCP Tool definition.

    Args:
        endpoint: Parsed OpenAPI endpoint

    Returns:
        MCP tool definition with name, description, inputSchema, and metadata
    """
    return {
        'name': generate_tool_name(endpoint),
        'description': _build_description(endpoint),
        'inputSchema': build_input_schema(endpoint),
        '_metadata': {
            'service': endpoint.service,
            'method': endpoint.method,
            'path': endpoint.path,
            'operation_id': endpoint.operation_id
        }
    }


def generate_tool_name(endpoint: OpenAPIEndpoint) -> str:
    """
    Generate MCP tool name from endpoint.

    Prefers operation_id if set, otherwise generates from path.

    Examples:
        operation_id="search_corporation" → search_corporation
        GET /api/market/price/{type_id} → get_market_price
        POST /api/market/bulk → post_market_bulk

    Args:
        endpoint: OpenAPI endpoint

    Returns:
        MCP-compatible tool name
    """
    # Prefer explicit operation_id if set
    if endpoint.operation_id:
        # Clean up auto-generated IDs (remove _api_mcp_* suffix patterns)
        # But keep clean operation_ids like "search_corporation"
        if '_api_' not in endpoint.operation_id:
            return endpoint.operation_id
        # If it's auto-generated, extract the function name
        parts = endpoint.operation_id.split('_api_')
        if parts:
            return parts[0]

    # Fallback: Generate from path
    # Remove /api prefix and filter empty parts
    path_parts = [p for p in endpoint.path.split('/') if p and p != 'api']

    # Remove parameter braces: {type_id} → type_id
    clean_parts = [p.strip('{}') for p in path_parts]

    # Build name: method_part1_part2_...
    method = endpoint.method.lower()
    name = f"{method}_{'_'.join(clean_parts)}"

    return name


def build_input_schema(endpoint: OpenAPIEndpoint) -> Dict[str, Any]:
    """
    Extract parameters from OpenAPI endpoint and build MCP inputSchema.

    Handles:
        - Path parameters: {type_id}
        - Query parameters: ?region_id=...
        - Request body: POST/PUT JSON payload

    Args:
        endpoint: OpenAPI endpoint

    Returns:
        MCP-compatible JSON Schema for tool inputs
    """
    properties = {}
    required = []

    # Process path & query parameters
    for param in endpoint.parameters:
        param_name = param.get('name')
        if not param_name:
            continue

        param_schema = param.get('schema', {})
        param_type = param_schema.get('type', 'string')

        properties[param_name] = {
            'type': map_openapi_type(param_type),
            'description': param.get('description', ''),
        }

        # Add default value if present
        if 'default' in param_schema:
            properties[param_name]['default'] = param_schema['default']

        # Track required parameters
        if param.get('required', False):
            required.append(param_name)

    # Process request body parameters
    if endpoint.request_body:
        content = endpoint.request_body.get('content', {})
        json_schema = content.get('application/json', {}).get('schema', {})

        # Extract properties from request body schema
        if json_schema.get('properties'):
            for prop_name, prop_schema in json_schema['properties'].items():
                prop_type = prop_schema.get('type', 'string')

                properties[prop_name] = {
                    'type': map_openapi_type(prop_type),
                    'description': prop_schema.get('description', ''),
                }

            # Add required body parameters
            required.extend(json_schema.get('required', []))

    return {
        'type': 'object',
        'properties': properties,
        'required': list(set(required))  # Deduplicate
    }


def map_openapi_type(openapi_type: str) -> str:
    """
    Map OpenAPI types to MCP/JSON Schema types.

    Args:
        openapi_type: OpenAPI type string

    Returns:
        MCP-compatible type string
    """
    type_map = {
        'integer': 'integer',
        'number': 'number',
        'string': 'string',
        'boolean': 'boolean',
        'array': 'array',
        'object': 'object'
    }
    return type_map.get(openapi_type, 'string')


def _build_description(endpoint: OpenAPIEndpoint) -> str:
    """
    Build tool description from endpoint summary and description.

    Args:
        endpoint: OpenAPI endpoint

    Returns:
        Combined description string
    """
    parts = []

    if endpoint.summary:
        parts.append(endpoint.summary)

    if endpoint.description and endpoint.description != endpoint.summary:
        parts.append(endpoint.description)

    return '\n\n'.join(parts).strip() or 'No description available'
