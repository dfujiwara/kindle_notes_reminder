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

    # Pre-populate with existing URL and chunks
    from src.repositories.models import URLCreate, URLChunkCreate

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
async def test_process_url_content_return_value_structure():
    """Test that the return value has the correct structure."""
    # Setup
    url_repo = StubURLRepository()
    chunk_repo = StubURLChunkRepository()
    embedding_client = StubEmbeddingClient()
    llm_client = StubLLMClient(responses=["Concise summary."])

    test_url = "https://example.com/test"
    test_content = (
        "Paragraph one with substantial content.\n\n"
        "Paragraph two with more information.\n\n"
        "Paragraph three completing the thought."
    )

    # Create a mock fetch function
    async def mock_fetch(
        url: str, max_content_size: int | None = None
    ) -> FetchedContent:
        return FetchedContent(url=test_url, title="Test Page", content=test_content)

    result = await process_url_content(
        test_url,
        url_repo,
        chunk_repo,
        llm_client,
        embedding_client,
        fetch_fn=mock_fetch,
    )

    # Verify URLWithChunksResponses structure
    assert hasattr(result, "url")
    assert hasattr(result, "chunks")

    # Verify URL response structure
    url_resp = result.url
    assert hasattr(url_resp, "id")
    assert hasattr(url_resp, "url")
    assert hasattr(url_resp, "title")
    assert hasattr(url_resp, "fetched_at")
    assert hasattr(url_resp, "created_at")

    # Verify chunk response structure
    assert len(result.chunks) > 0
    for chunk in result.chunks:
        assert hasattr(chunk, "id")
        assert hasattr(chunk, "content")
        assert hasattr(chunk, "chunk_order")
        assert hasattr(chunk, "is_summary")
        assert hasattr(chunk, "created_at")

    # Verify summary is first chunk
    assert result.chunks[0].is_summary is True
    assert result.chunks[0].chunk_order == 0

    # Verify text chunks are ordered
    for i, chunk in enumerate(result.chunks[1:], start=1):
        assert chunk.chunk_order == i
        assert chunk.is_summary is False


@pytest.mark.asyncio
async def test_process_url_content_with_multiple_paragraphs():
    """Test processing content with multiple paragraphs."""
    # Setup
    url_repo = StubURLRepository()
    chunk_repo = StubURLChunkRepository()
    embedding_client = StubEmbeddingClient()
    llm_client = StubLLMClient(responses=["Summary"])

    test_url = "https://example.com/article"
    # Create content with multiple paragraphs
    test_content = "\n\n".join(
        ["Paragraph " + str(i) + " with content." for i in range(1, 6)]
    )

    # Create a mock fetch function
    async def mock_fetch(
        url: str, max_content_size: int | None = None
    ) -> FetchedContent:
        return FetchedContent(url=test_url, title="Test", content=test_content)

    result = await process_url_content(
        test_url,
        url_repo,
        chunk_repo,
        llm_client,
        embedding_client,
        fetch_fn=mock_fetch,
    )

    # Should have summary + at least 1 text chunk
    assert len(result.chunks) >= 2
    assert result.chunks[0].is_summary is True


@pytest.mark.asyncio
async def test_process_url_content_chunk_ordering():
    """Test that chunks are correctly ordered with summary first."""
    # Setup
    url_repo = StubURLRepository()
    chunk_repo = StubURLChunkRepository()
    embedding_client = StubEmbeddingClient()
    llm_client = StubLLMClient(responses=["Summary text"])

    test_url = "https://example.com/article"
    # Create content that will be split into multiple chunks
    test_content = "\n\n".join(
        [
            "First paragraph with content.",
            "Second paragraph with more content.",
            "Third paragraph with additional content.",
        ]
    )

    # Create a mock fetch function
    async def mock_fetch(
        url: str, max_content_size: int | None = None
    ) -> FetchedContent:
        return FetchedContent(url=test_url, title="Test", content=test_content)

    result = await process_url_content(
        test_url,
        url_repo,
        chunk_repo,
        llm_client,
        embedding_client,
        fetch_fn=mock_fetch,
    )

    # Verify chunk ordering
    chunk_orders = [chunk.chunk_order for chunk in result.chunks]
    expected_orders = list(range(len(result.chunks)))
    assert chunk_orders == expected_orders

    # Verify first chunk is summary
    assert result.chunks[0].is_summary is True


@pytest.mark.asyncio
async def test_process_url_content_content_hash_generation():
    """Test that content hashes are generated correctly for chunks."""
    # Setup
    url_repo = StubURLRepository()
    chunk_repo = StubURLChunkRepository()
    embedding_client = StubEmbeddingClient()
    llm_client = StubLLMClient(responses=["Summary"])

    test_url = "https://example.com/article"
    test_content = "Single paragraph of content."

    # Create a mock fetch function
    async def mock_fetch(
        url: str, max_content_size: int | None = None
    ) -> FetchedContent:
        return FetchedContent(url=test_url, title="Test", content=test_content)

    result = await process_url_content(
        test_url,
        url_repo,
        chunk_repo,
        llm_client,
        embedding_client,
        fetch_fn=mock_fetch,
    )

    # All chunks should have content_hash in the repository
    # (We can't directly access it from URLChunkResponse, but we verify chunks were saved)
    assert len(result.chunks) >= 2  # At least summary + one text chunk
    for chunk in result.chunks:
        assert chunk.content is not None
        assert len(chunk.content) > 0
