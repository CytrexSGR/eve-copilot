# tests/integration/test_mcp_doctrine_tools.py
"""Integration tests for doctrine MCP tools."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


@pytest.mark.integration
class TestDoctrineMCPTools:
    def test_list_tools_includes_doctrine(self, client):
        response = client.get("/mcp/tools/list")

        assert response.status_code == 200
        data = response.json()
        tools = data["tools"]
        tool_names = [t["name"] for t in tools]

        assert "get_doctrine_templates" in tool_names
        assert "analyze_fleet" in tool_names

    def test_call_get_doctrine_templates(self, client):
        response = client.post("/mcp/tools/call", json={
            "name": "get_doctrine_templates",
            "arguments": {}
        })

        assert response.status_code == 200
        result = response.json()
        assert "result" in result
        assert len(result["result"]) >= 14

    def test_call_analyze_fleet_not_found(self, client):
        response = client.post("/mcp/tools/call", json={
            "name": "analyze_fleet",
            "arguments": {"killmail_id": 999999999}
        })

        assert response.status_code == 200
        result = response.json()
        assert result["result"] is None
