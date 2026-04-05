"""Tests for ServiceConfig base class."""

from eve_shared.config import ServiceConfig


class TestServiceConfigCors:
    """Tests for cors_origin_list property on ServiceConfig."""

    def test_cors_wildcard(self):
        config = ServiceConfig(cors_origins="*")
        assert config.cors_origin_list == ["*"]

    def test_cors_multiple(self):
        config = ServiceConfig(cors_origins="http://localhost:3000, http://example.com")
        assert config.cors_origin_list == ["http://localhost:3000", "http://example.com"]

    def test_cors_empty_entries_filtered(self):
        config = ServiceConfig(cors_origins="http://a.com, , http://b.com")
        assert config.cors_origin_list == ["http://a.com", "http://b.com"]

    def test_cors_default_is_wildcard(self):
        config = ServiceConfig()
        assert config.cors_origin_list == ["*"]

    def test_cors_single_origin(self):
        config = ServiceConfig(cors_origins="http://localhost:5173")
        assert config.cors_origin_list == ["http://localhost:5173"]

    def test_cors_trailing_comma(self):
        config = ServiceConfig(cors_origins="http://a.com,")
        assert config.cors_origin_list == ["http://a.com"]
