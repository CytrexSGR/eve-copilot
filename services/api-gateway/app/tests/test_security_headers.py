"""Tests for security header configuration."""
import pytest


class TestCorsOriginParsing:
    """Test CORS origin string parsing logic."""

    def test_wildcard(self):
        from app.main import _parse_cors_origins
        assert _parse_cors_origins("*") == ["*"]

    def test_single_origin(self):
        from app.main import _parse_cors_origins
        assert _parse_cors_origins("https://eve.infinimind-creations.com") == [
            "https://eve.infinimind-creations.com"
        ]

    def test_multiple_origins(self):
        from app.main import _parse_cors_origins
        result = _parse_cors_origins(
            "https://eve.infinimind-creations.com,http://localhost:5175,http://localhost:5173"
        )
        assert len(result) == 3
        assert "https://eve.infinimind-creations.com" in result
        assert "http://localhost:5175" in result

    def test_strips_whitespace(self):
        from app.main import _parse_cors_origins
        result = _parse_cors_origins(" https://a.com , https://b.com ")
        assert result == ["https://a.com", "https://b.com"]

    def test_empty_string(self):
        from app.main import _parse_cors_origins
        assert _parse_cors_origins("") == ["*"]

    def test_none_defaults_to_wildcard(self):
        from app.main import _parse_cors_origins
        assert _parse_cors_origins(None) == ["*"]
