"""CORS configuration for the FastAPI application."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _normalize_origin(origin: str) -> str:
    """
    Normalize a CORS origin by adding https:// if no protocol is specified.

    Args:
        origin: The origin string (e.g., "example.com" or "https://example.com")

    Returns:
        The normalized origin with protocol (e.g., "https://example.com")
    """
    if not origin.startswith(("http://", "https://")):
        return f"https://{origin}"
    return origin


def _get_cors_origins(production_origin: str | None = None) -> list[str]:
    """
    Get the list of allowed CORS origins.

    Args:
        production_origin: Optional production origin. If provided, uses that
                          (normalized with protocol). Otherwise, returns default
                          development origins (localhost:5173, etc.)

    Returns:
        List of allowed CORS origins with protocols
    """
    default_origins = [
        "http://localhost:5173",  # Vite default dev server
        "http://127.0.0.1:5173",  # IPv4 localhost variant
        "http://localhost:4173",  # Vite production preview server
        "http://127.0.0.1:4173",  # IPv4 localhost variant
    ]

    if production_origin:
        normalized = _normalize_origin(production_origin)
        return [normalized]

    return default_origins


def get_cors_config(production_origin: str | None = None) -> dict[str, Any]:
    """
    Get the CORS middleware configuration.

    Args:
        production_origin: Optional production origin. If provided, only this
                          origin will be allowed (normalized with https:// if
                          no protocol specified). If not provided, default
                          development origins are used.

    Returns:
        Dictionary with CORS configuration including allow_origins,
        allow_credentials, allow_methods, and allow_headers
    """
    allowed_origins = _get_cors_origins(production_origin)
    logger.info(f"CORS allowed_origins setting is {allowed_origins}")

    return {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
