"""
Utilities for Server-Sent Events (SSE) streaming.
"""

import json
from typing import Any


def format_sse(event: str, data: dict[str, Any]) -> str:
    """
    Format data as Server-Sent Event with event type and data.

    :param event: The event type (e.g., 'metadata', 'context_chunk', 'error')
    :param data: The data to send, will be JSON-encoded
    :return: Formatted SSE string with event and data fields
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
