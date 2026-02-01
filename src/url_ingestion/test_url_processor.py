"""Tests for the URL content processing pipeline."""

import json

import pytest
from src.url_ingestion.url_processor import (
    process_url_content,
)
from src.url_ingestion.url_fetcher import FetchedContent, URLFetcherInterface
from src.test_utils import (
    StubURLRepository,
    StubURLChunkRepository,
    StubEmbeddingClient,
    StubLLMClient,
)
from src.repositories.models import URLCreate, URLChunkCreate


LONG_CONTENT = "A" * 100  # Must be >= 50 chars to pass semantic chunking check


@pytest.fixture
def mock_simple_fetcher():
    """Mock URL fetcher returning simple content."""

    async def _mock_fetch(
        url: str, max_content_size: int | None = None
    ) -> FetchedContent:
        return FetchedContent(
            url=url,
            title="Test Article",
            content=LONG_CONTENT,
        )

    return _mock_fetch


@pytest.fixture
def mock_fetcher_should_not_be_called():
    """Mock URL fetcher that fails if called."""

    async def _mock_fetch(
        url: str, max_content_size: int | None = None
    ) -> FetchedContent:
        raise AssertionError("fetch should not be called for existing URLs")

    return _mock_fetch


@pytest.mark.asyncio
async def test_process_url_content_success(mock_simple_fetcher: URLFetcherInterface):
    """Test successful processing of a new URL with content chunking and embedding."""
    # Setup
    url_repo = StubURLRepository()
    chunk_repo = StubURLChunkRepository()
    embedding_client = StubEmbeddingClient()
    semantic_response = json.dumps({"chunks": [LONG_CONTENT]})
    llm_client = StubLLMClient(responses=[semantic_response, "This is a test summary."])

    test_url = "https://example.com/article"

    # Call the function with injected mock
    result = await process_url_content(
        test_url,
        url_repo,
        chunk_repo,
        llm_client,
        embedding_client,
        fetch_fn=mock_simple_fetcher,
    )

    # Assertions on URL
    assert result.url.url == test_url
    assert result.url.title == "Test Article"
    assert result.url.id == 1

    # Assertions on chunks
    assert len(result.chunks) == 2  # 1 summary + 1 text chunk

    # Check summary chunk (chunk_order=0, is_summary=True)
    summary_chunk = result.chunks[0]
    assert summary_chunk.chunk_order == 0
    assert summary_chunk.is_summary is True
    assert summary_chunk.content == "This is a test summary."

    # Check text chunk
    text_chunk = result.chunks[1]
    assert text_chunk.chunk_order == 1
    assert text_chunk.is_summary is False
    assert text_chunk.content == LONG_CONTENT


@pytest.mark.asyncio
async def test_process_url_content_duplicate_url_returns_existing(
    mock_fetcher_should_not_be_called: URLFetcherInterface,
):
    """Test that duplicate URLs are not re-fetched and existing record is returned."""
    # Setup
    url_repo = StubURLRepository()
    chunk_repo = StubURLChunkRepository()
    embedding_client = StubEmbeddingClient()
    llm_client = StubLLMClient()

    test_url = "https://example.com/article"

    url_record = url_repo.add(URLCreate(url=test_url, title="Existing Article"))
    chunk_repo.add(
        URLChunkCreate(
            content="Summary content",
            content_hash="hash1",
            url_id=url_record.id,
            chunk_order=0,
            is_summary=True,
        )
    )
    chunk_repo.add(
        URLChunkCreate(
            content="Body content",
            content_hash="hash2",
            url_id=url_record.id,
            chunk_order=1,
            is_summary=False,
        )
    )

    result = await process_url_content(
        test_url,
        url_repo,
        chunk_repo,
        llm_client,
        embedding_client,
        fetch_fn=mock_fetcher_should_not_be_called,
    )

    # Should return existing URL
    assert result.url.url == test_url
    assert result.url.title == "Existing Article"
    assert len(result.chunks) == 2


@pytest.mark.asyncio
async def test_process_url_content_falls_back_to_paragraph_chunking(
    mock_simple_fetcher: URLFetcherInterface,
):
    """Test that pipeline falls back to paragraph chunking when semantic chunking fails."""
    url_repo = StubURLRepository()
    chunk_repo = StubURLChunkRepository()
    embedding_client = StubEmbeddingClient()
    # First response (semantic chunking) is invalid JSON → triggers fallback
    # Second response is the summary
    llm_client = StubLLMClient(responses=["not valid json", "Summary text."])

    result = await process_url_content(
        "https://example.com/fallback",
        url_repo,
        chunk_repo,
        llm_client,
        embedding_client,
        fetch_fn=mock_simple_fetcher,
    )

    # Should still succeed with paragraph-based chunks
    assert result.url.url == "https://example.com/fallback"
    assert result.chunks[0].is_summary is True
    assert result.chunks[0].content == "Summary text."
    # At least one paragraph chunk from the fallback
    text_chunks = [c for c in result.chunks if not c.is_summary]
    assert len(text_chunks) >= 1
