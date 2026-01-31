"""Tests for LLM-based semantic chunking."""

import json

import pytest

from src.test_utils import StubLLMClient
from src.url_ingestion.semantic_chunker import (
    MAX_CONTENT_SIZE,
    SemanticChunkingError,
    SemanticChunkingResult,
    chunk_content_with_llm,
)


# --- SemanticChunkingResult validation ---


def test_result_valid():
    result = SemanticChunkingResult(chunks=["hello", "world"])
    assert result.chunks == ["hello", "world"]


def test_result_strips_whitespace():
    result = SemanticChunkingResult(chunks=["  hello  ", "\nworld\n"])
    assert result.chunks == ["hello", "world"]


def test_result_filters_empty_strings():
    result = SemanticChunkingResult(chunks=["hello", "", "  ", "world"])
    assert result.chunks == ["hello", "world"]


def test_result_chunks_not_list():
    with pytest.raises(ValueError, match="must be a list"):
        SemanticChunkingResult(chunks="not a list")  # type: ignore[arg-type]


def test_result_empty_chunks_list():
    with pytest.raises(ValueError, match="at least one non-empty"):
        SemanticChunkingResult(chunks=[])


def test_result_all_empty_chunks():
    with pytest.raises(ValueError, match="at least one non-empty"):
        SemanticChunkingResult(chunks=["", "  ", "\n"])


def test_result_non_string_chunks_filtered():
    """Non-string chunks are silently filtered; if none remain, validation fails."""
    with pytest.raises(ValueError, match="at least one non-empty"):
        SemanticChunkingResult(chunks=[123])  # type: ignore[list-item]


# --- chunk_content_with_llm ---


@pytest.mark.asyncio
async def test_chunk_content_success():
    stub_llm = StubLLMClient(responses=[json.dumps({"chunks": ["chunk1", "chunk2"]})])

    result = await chunk_content_with_llm(stub_llm, "A" * 100)

    assert result.chunks == ["chunk1", "chunk2"]
    assert stub_llm.call_count == 1


@pytest.mark.asyncio
async def test_chunk_content_too_short():
    stub_llm = StubLLMClient()

    with pytest.raises(SemanticChunkingError, match="too short"):
        await chunk_content_with_llm(stub_llm, "short")

    assert stub_llm.call_count == 0


@pytest.mark.asyncio
async def test_chunk_content_truncates_large_content():
    stub_llm = StubLLMClient(responses=[json.dumps({"chunks": ["chunk"]})])

    large_content = "A" * (MAX_CONTENT_SIZE + 1000)
    await chunk_content_with_llm(stub_llm, large_content)

    assert stub_llm.call_count == 1


@pytest.mark.asyncio
async def test_chunk_content_llm_error():
    stub_llm = StubLLMClient(should_fail=True)

    with pytest.raises(SemanticChunkingError, match="LLM request failed"):
        await chunk_content_with_llm(stub_llm, "A" * 100)


@pytest.mark.asyncio
async def test_chunk_content_invalid_llm_response():
    stub_llm = StubLLMClient(responses=["not json"])

    with pytest.raises(SemanticChunkingError, match="Failed to parse"):
        await chunk_content_with_llm(stub_llm, "A" * 100)


@pytest.mark.asyncio
async def test_chunk_content_missing_chunks_field():
    stub_llm = StubLLMClient(responses=[json.dumps({"other": "data"})])

    with pytest.raises(SemanticChunkingError, match="Invalid chunking result"):
        await chunk_content_with_llm(stub_llm, "A" * 100)
