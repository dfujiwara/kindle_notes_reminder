"""
Tests for the additional_context module.

Tests both the regular and streaming versions of get_additional_context.
"""

import pytest
from src.additional_context import (
    get_additional_context,
    get_additional_context_stream,
)
from src.repositories.models import BookResponse, NoteRead
from src.test_utils import StubLLMClient
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_get_additional_context_success():
    """Test successful additional context generation."""
    mock_response = "This book discusses software engineering best practices."
    llm_client = StubLLMClient(responses=[mock_response])

    book = BookResponse(
        id=1,
        title="The Pragmatic Programmer",
        author="David Thomas",
        created_at=datetime.now(timezone.utc),
    )
    note = NoteRead(
        id=1,
        book_id=1,
        content="Always use version control.",
        content_hash="abc123",
        created_at=datetime.now(timezone.utc),
    )

    result = await get_additional_context(llm_client, book, note)

    assert result.response == mock_response
    assert "The Pragmatic Programmer" in result.prompt
    assert "Always use version control" in result.prompt
    assert "context_provider" in result.system or len(result.system) > 0
    assert llm_client.call_count == 1


@pytest.mark.asyncio
async def test_get_additional_context_stream_success():
    """Test that streaming yields multiple chunks and combines to full response."""
    # Create a long response that will be split into chunks
    long_response = "A" * 100  # 100 characters
    llm_client = StubLLMClient(responses=[long_response])

    book = BookResponse(
        id=1,
        title="Test Book",
        author="Test Author",
        created_at=datetime.now(timezone.utc),
    )
    note = NoteRead(
        id=1,
        book_id=1,
        content="Test content",
        content_hash="abc123",
        created_at=datetime.now(timezone.utc),
    )

    chunks: list[str] = []
    final_chunk = None
    async for chunk in get_additional_context_stream(llm_client, book, note):
        if chunk.is_complete:
            final_chunk = chunk
        else:
            chunks.append(chunk.content)

    # Verify streaming behavior: StubLLMClient splits into chunks of size 10
    assert len(chunks) == 10
    assert all(len(chunk) == 10 for chunk in chunks)

    # Verify chunks combine to the full response
    assert "".join(chunks) == long_response

    # Verify we got the final chunk with metadata
    assert final_chunk is not None
    assert final_chunk.is_complete is True
    assert final_chunk.content == long_response
    assert final_chunk.llm_prompt_response is not None
    assert final_chunk.llm_prompt_response.response == long_response
    assert "Test Book" in final_chunk.llm_prompt_response.prompt
    assert "Test content" in final_chunk.llm_prompt_response.prompt

    # Verify LLM was called
    assert llm_client.call_count == 1
