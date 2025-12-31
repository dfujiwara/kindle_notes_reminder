"""
Tests for URL management endpoints in urls.py

Tests URL ingestion, listing, and chunk retrieval endpoints.
"""

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from ..main import app
from ..dependencies import (
    get_url_repository,
    get_urlchunk_repository,
    get_llm_client,
    get_embedding_client,
)
from ..repositories.models import (
    URLCreate,
    URLChunkCreate,
    URLResponse,
    URLChunkResponse,
    URLWithChunksResponses,
)
from ..test_utils import (
    StubURLRepository,
    StubURLChunkRepository,
    StubLLMClient,
    StubEmbeddingClient,
)
from ..url_ingestion.url_fetcher import FetchedContent, URLFetchError

client = TestClient(app)


def test_ingest_url_already_exists():
    """Test ingesting a URL that already exists returns the existing record."""
    url_repo = StubURLRepository()
    chunk_repo = StubURLChunkRepository()
    llm_client = StubLLMClient(responses=["Test summary"])
    embedding_client = StubEmbeddingClient()

    app.dependency_overrides[get_url_repository] = lambda: url_repo
    app.dependency_overrides[get_urlchunk_repository] = lambda: chunk_repo
    app.dependency_overrides[get_llm_client] = lambda: llm_client
    app.dependency_overrides[get_embedding_client] = lambda: embedding_client

    try:
        # Pre-populate with an existing URL
        created_at = datetime.now(timezone.utc)
        existing_url = url_repo.add(
            URLCreate(
                url="https://example.com",
                title="Example Article",
            )
        )
        chunk_repo.add(
            URLChunkCreate(
                content="Test content",
                content_hash="hash1",
                url_id=existing_url.id,
                chunk_order=0,
                is_summary=True,
                embedding=[0.1] * 1536,
            )
        )

        # Try to ingest the same URL
        mock_fetched_content = FetchedContent(
            url="https://example.com",
            title="Different Title (should not be used)",
            content="Different content (should not be used)",
        )

        with patch(
            "src.url_ingestion.url_processor.fetch_url_content",
            new_callable=AsyncMock,
            return_value=mock_fetched_content,
        ):
            response = client.post("/urls", json={"url": "https://example.com"})

        assert response.status_code == 200
        data = response.json()
        # Should return the existing URL, not refetch
        assert data["url"]["url"] == "https://example.com"
        assert data["url"]["title"] == "Example Article"  # Original title
        assert len(data["chunks"]) == 1  # Original chunk count
    finally:
        app.dependency_overrides.clear()


def test_ingest_url_fetch_error():
    """Test URL fetch error returns 400."""
    url_repo = StubURLRepository()
    chunk_repo = StubURLChunkRepository()
    llm_client = StubLLMClient()
    embedding_client = StubEmbeddingClient()

    app.dependency_overrides[get_url_repository] = lambda: url_repo
    app.dependency_overrides[get_urlchunk_repository] = lambda: chunk_repo
    app.dependency_overrides[get_llm_client] = lambda: llm_client
    app.dependency_overrides[get_embedding_client] = lambda: embedding_client

    try:
        with patch(
            "src.url_ingestion.url_processor.fetch_url_content",
            new_callable=AsyncMock,
            side_effect=URLFetchError("Failed to fetch URL"),
        ):
            response = client.post("/urls", json={"url": "https://invalid.com"})

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "URL fetch error" in data["detail"]
    finally:
        app.dependency_overrides.clear()


def test_get_urls_empty():
    """Test GET /urls returns empty list when no URLs exist."""
    url_repo = StubURLRepository()
    chunk_repo = StubURLChunkRepository()

    app.dependency_overrides[get_url_repository] = lambda: url_repo
    app.dependency_overrides[get_urlchunk_repository] = lambda: chunk_repo

    try:
        response = client.get("/urls")

        assert response.status_code == 200
        data = response.json()
        assert "urls" in data
        assert len(data["urls"]) == 0
    finally:
        app.dependency_overrides.clear()


def test_get_urls_with_urls():
    """Test GET /urls returns all URLs with chunk counts."""
    url_repo = StubURLRepository()
    chunk_repo = StubURLChunkRepository()

    app.dependency_overrides[get_url_repository] = lambda: url_repo
    app.dependency_overrides[get_urlchunk_repository] = lambda: chunk_repo

    try:
        # Create test data
        url1 = url_repo.add(URLCreate(url="https://example1.com", title="Example 1"))
        url2 = url_repo.add(URLCreate(url="https://example2.com", title="Example 2"))

        # Add chunks to first URL
        chunk_repo.add(
            URLChunkCreate(
                content="Content 1",
                content_hash="hash1",
                url_id=url1.id,
                chunk_order=0,
                is_summary=True,
                embedding=[0.1] * 1536,
            )
        )
        chunk_repo.add(
            URLChunkCreate(
                content="Content 2",
                content_hash="hash2",
                url_id=url1.id,
                chunk_order=1,
                is_summary=False,
                embedding=[0.2] * 1536,
            )
        )

        # Add chunks to second URL
        chunk_repo.add(
            URLChunkCreate(
                content="Content 3",
                content_hash="hash3",
                url_id=url2.id,
                chunk_order=0,
                is_summary=True,
                embedding=[0.3] * 1536,
            )
        )

        response = client.get("/urls")

        assert response.status_code == 200
        data = response.json()
        assert "urls" in data
        assert len(data["urls"]) == 2

        # Check first URL
        url1_response = next((u for u in data["urls"] if u["id"] == url1.id), None)
        assert url1_response is not None
        assert url1_response["url"] == "https://example1.com"
        assert url1_response["title"] == "Example 1"
        assert url1_response["chunk_count"] == 2

        # Check second URL
        url2_response = next((u for u in data["urls"] if u["id"] == url2.id), None)
        assert url2_response is not None
        assert url2_response["url"] == "https://example2.com"
        assert url2_response["title"] == "Example 2"
        assert url2_response["chunk_count"] == 1
    finally:
        app.dependency_overrides.clear()


def test_ingest_url_invalid_request():
    """Test POST /urls with invalid request data."""
    url_repo = StubURLRepository()
    chunk_repo = StubURLChunkRepository()

    app.dependency_overrides[get_url_repository] = lambda: url_repo
    app.dependency_overrides[get_urlchunk_repository] = lambda: chunk_repo

    try:
        # Missing required url field
        response = client.post("/urls", json={})

        assert response.status_code == 422  # Validation error
    finally:
        app.dependency_overrides.clear()


def test_ingest_url_empty_string():
    """Test POST /urls with empty URL string."""
    url_repo = StubURLRepository()
    chunk_repo = StubURLChunkRepository()

    app.dependency_overrides[get_url_repository] = lambda: url_repo
    app.dependency_overrides[get_urlchunk_repository] = lambda: chunk_repo

    try:
        response = client.post("/urls", json={"url": ""})

        assert response.status_code == 422  # Validation error due to min_length=1
    finally:
        app.dependency_overrides.clear()
