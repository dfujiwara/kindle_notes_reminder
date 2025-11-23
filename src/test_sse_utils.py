"""
Tests for Server-Sent Events (SSE) utilities.
"""

import json

from src.sse_utils import format_sse


def test_sse_format():
    """Test SSE format structure: event line, data line, double newline."""
    result = format_sse("test", {"key": "value"})
    assert result == 'event: test\ndata: {"key": "value"}\n\n'


def test_json_serialization():
    """Test various data types are correctly serialized to JSON."""
    data = {
        "nested": {"id": 1},
        "str": "café",
        "int": 42,
        "bool": True,
        "null": None,
        "list": [1, 2],
        "special": 'Line\n"quote"',
    }
    result = format_sse("event", data)
    json_part = result.split("data: ")[1].rstrip("\n")
    assert json.loads(json_part) == data
