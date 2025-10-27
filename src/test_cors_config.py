"""Tests for CORS configuration."""

from src.cors_config import get_cors_config


def test_get_cors_config_default():
    """Test that default origins are returned when no production origin is provided"""
    config = get_cors_config()
    assert "allow_origins" in config
    assert "allow_credentials" in config
    assert "allow_methods" in config
    assert "allow_headers" in config

    origins = config["allow_origins"]
    assert len(origins) == 4
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    assert "http://localhost:4173" in origins
    assert "http://127.0.0.1:4173" in origins

    assert config["allow_credentials"] is True
    assert config["allow_methods"] == ["*"]
    assert config["allow_headers"] == ["*"]


def test_get_cors_config_with_production_origin_no_protocol():
    """Test that production origin without protocol gets normalized to https://"""
    config = get_cors_config(production_origin="example.com")
    assert config["allow_origins"] == ["https://example.com"]


def test_get_cors_config_with_production_origin_with_https():
    """Test that production origin with https:// is used as-is"""
    config = get_cors_config(production_origin="https://secure.example.com")
    assert config["allow_origins"] == ["https://secure.example.com"]


def test_get_cors_config_with_production_origin_with_http():
    """Test that production origin with http:// is used as-is"""
    config = get_cors_config(production_origin="http://local.example.com")
    assert config["allow_origins"] == ["http://local.example.com"]


def test_get_cors_config_with_none_uses_defaults():
    """Test that explicitly passing None returns default origins"""
    config = get_cors_config(production_origin=None)
    origins = config["allow_origins"]
    assert len(origins) == 4
    assert "http://localhost:5173" in origins


def test_get_cors_config_with_empty_string_uses_defaults():
    """Test that empty string is treated as no production origin"""
    config = get_cors_config(production_origin="")
    origins = config["allow_origins"]
    assert len(origins) == 4
    assert "http://localhost:5173" in origins
