"""Tests for error handling decorator and exception classification."""

import pytest
from fastapi import HTTPException

from eve_shared.utils.error_handling import _handle_exception, handle_endpoint_errors


class TestHandleException:
    def test_http_exception_reraised(self):
        """HTTPException is re-raised via decorator, not _handle_exception directly.
        bare `raise` in _handle_exception requires active exception context."""
        @handle_endpoint_errors()
        def endpoint_raises_http():
            raise HTTPException(status_code=404, detail="Not found")

        with pytest.raises(HTTPException) as exc_info:
            endpoint_raises_http()
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"

    def test_value_error_becomes_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _handle_exception("test_func", ValueError("bad input"), 500, False)
        assert exc_info.value.status_code == 400
        assert "bad input" in exc_info.value.detail

    def test_key_error_becomes_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _handle_exception("test_func", KeyError("missing_field"), 500, False)
        assert exc_info.value.status_code == 400
        assert "missing_field" in exc_info.value.detail

    def test_generic_exception_becomes_default_status(self):
        with pytest.raises(HTTPException) as exc_info:
            _handle_exception("test_func", RuntimeError("boom"), 500, False)
        assert exc_info.value.status_code == 500

    def test_custom_default_status(self):
        with pytest.raises(HTTPException) as exc_info:
            _handle_exception("test_func", RuntimeError("boom"), 503, False)
        assert exc_info.value.status_code == 503

    def test_http_exception_preserves_status(self):
        """HTTPException with custom status is re-raised unchanged via decorator."""
        @handle_endpoint_errors()
        def endpoint_raises_429():
            raise HTTPException(status_code=429, detail="Rate limited")

        with pytest.raises(HTTPException) as exc_info:
            endpoint_raises_429()
        assert exc_info.value.status_code == 429


class TestHandleEndpointErrorsDecorator:
    def test_sync_function_success(self):
        @handle_endpoint_errors()
        def my_endpoint():
            return {"result": "ok"}

        assert my_endpoint() == {"result": "ok"}

    def test_sync_function_value_error(self):
        @handle_endpoint_errors()
        def bad_endpoint():
            raise ValueError("invalid param")

        with pytest.raises(HTTPException) as exc_info:
            bad_endpoint()
        assert exc_info.value.status_code == 400

    def test_sync_function_generic_error(self):
        @handle_endpoint_errors(default_status=502)
        def broken_endpoint():
            raise RuntimeError("connection failed")

        with pytest.raises(HTTPException) as exc_info:
            broken_endpoint()
        assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        @handle_endpoint_errors()
        async def my_async_endpoint():
            return {"async": True}

        result = await my_async_endpoint()
        assert result == {"async": True}

    @pytest.mark.asyncio
    async def test_async_function_error(self):
        @handle_endpoint_errors()
        async def bad_async():
            raise KeyError("missing")

        with pytest.raises(HTTPException) as exc_info:
            await bad_async()
        assert exc_info.value.status_code == 400

    def test_decorator_preserves_function_name(self):
        @handle_endpoint_errors()
        def my_named_endpoint():
            pass

        assert my_named_endpoint.__name__ == "my_named_endpoint"

    def test_decorator_preserves_async_function_name(self):
        @handle_endpoint_errors()
        async def my_async_named():
            pass

        assert my_async_named.__name__ == "my_async_named"
