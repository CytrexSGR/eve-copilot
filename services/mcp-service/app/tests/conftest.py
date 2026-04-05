"""Shared fixtures for mcp-service tests."""

import pytest
from app.openapi.parser import OpenAPIEndpoint


@pytest.fixture
def make_endpoint():
    """Factory fixture for creating OpenAPIEndpoint instances with defaults."""

    def _make(
        service="market",
        method="GET",
        path="/api/market/price/{type_id}",
        operation_id="",
        summary="",
        description="",
        parameters=None,
        request_body=None,
        responses=None,
        tags=None,
    ):
        return OpenAPIEndpoint(
            service=service,
            method=method,
            path=path,
            operation_id=operation_id,
            summary=summary,
            description=description,
            parameters=parameters or [],
            request_body=request_body,
            responses=responses or {},
            tags=tags or [],
        )

    return _make
