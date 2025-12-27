"""Tests for the URL content processing pipeline."""

import pytest
from src.url_ingestion.url_processor import process_url_content
from src.url_ingestion.url_fetcher import FetchedContent, URLFetcherInterface
from src.test_utils import (
    StubURLRepository,
    StubURLChunkRepository,
    StubEmbeddingClient,
    StubLLMClient,
)
from src.repositories.models import URLCreate, URLChunkCreate


@pytest.fixture
def mock_simple_fetcher():
    """Mock URL fetcher returning simple content."""

    async def _mock_fetch(
        url: str, max_content_size: int | None = None
    ) -> FetchedContent:
        return FetchedContent(
            url=url,
            title="Test Article",
            content="Content paragraph.",
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
    llm_client = StubLLMClient(responses=["This is a test summary."])

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

    # Check that remaining chunks are text chunks with proper ordering
    for i, chunk in enumerate(result.chunks[1:], start=1):
        assert chunk.chunk_order == i
        assert chunk.is_summary is False
        assert len(chunk.content) > 0


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
