"""
Tests for URL management endpoints in urls.py

Tests URL ingestion, listing, and chunk retrieval endpoints.
"""

from fastapi.testclient import TestClient

from src.routers.conftest import URLDepsSetup
from ..main import app
from ..repositories.models import URLCreate, URLChunkCreate

client = TestClient(app)


def test_ingest_url_fetch_error(setup_url_deps: URLDepsSetup):
    """Test URL fetch error returns 422 (unprocessable entity)."""
    _, _, fetcher = setup_url_deps(fetcher_should_fail=True)

    response = client.post("/urls", json={"url": "https://invalid.com"})

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "Cannot process URL" in data["detail"]
    assert len(fetcher.calls) == 1  # Verify fetcher was called
    # URL is normalized with trailing slash by pydantic.HttpUrl
    assert fetcher.calls[0] == "https://invalid.com/"


def test_ingest_url_success(setup_url_deps: URLDepsSetup):
    """Test successful URL ingestion returns 200 with chunks stored."""
    url_repo, chunk_repo, _ = setup_url_deps()

    response = client.post("/urls", json={"url": "https://example.com"})

    assert response.status_code == 200
    data = response.json()

    # Verify URL was stored
    assert data["url"]["url"] == "https://example.com/"
    assert data["url"]["title"] == "Test: https://example.com/"

    # Verify URL is in repository
    stored_url = url_repo.get_by_url("https://example.com/")
    assert stored_url is not None

    # Verify chunks were created and stored
    chunks = chunk_repo.get_by_url_id(stored_url.id)
    assert len(chunks) == 2

    # Verify chunk structure
    for chunk in chunks:
        assert chunk.url_id == stored_url.id
        expected_content = (
            "Test LLM response"
            if chunk.is_summary
            else "Test content from stub fetcher."
        )
        assert chunk.content == expected_content
        assert chunk.embedding == [0.1] * 1536


def test_get_urls_empty(setup_url_deps: URLDepsSetup):
    """Test GET /urls returns empty list when no URLs exist."""
    setup_url_deps()

    response = client.get("/urls")

    assert response.status_code == 200
    data = response.json()
    assert len(data["urls"]) == 0


def test_get_urls_with_urls(setup_url_deps: URLDepsSetup):
    """Test GET /urls returns all URLs with chunk counts."""
    url_repo, chunk_repo, _ = setup_url_deps()

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


def test_ingest_url_invalid_request(setup_url_deps: URLDepsSetup):
    """Test POST /urls with invalid request data."""
    setup_url_deps()

    # Missing required url field
    response = client.post("/urls", json={})

    assert response.status_code == 422  # Validation error


def test_ingest_url_invalid_format(setup_url_deps: URLDepsSetup):
    """Test POST /urls with invalid URL format."""
    setup_url_deps()

    # Test with invalid URL format
    response = client.post("/urls", json={"url": "not a valid url"})

    assert response.status_code == 422  # Validation error from pydantic.HttpUrl
    data = response.json()
    assert "detail" in data


def test_get_url_with_chunks_not_found(setup_url_deps: URLDepsSetup):
    """Test GET /urls/{url_id} returns 404 when URL doesn't exist."""
    setup_url_deps()

    response = client.get("/urls/999")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "URL not found"


def test_get_url_with_chunks_empty(setup_url_deps: URLDepsSetup):
    """Test GET /urls/{url_id} returns URL with empty chunks when no chunks exist."""
    url_repo, _, _ = setup_url_deps()

    # Create URL without chunks
    url = url_repo.add(URLCreate(url="https://example.com", title="Example"))

    response = client.get(f"/urls/{url.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["url"]["id"] == url.id
    assert data["url"]["url"] == "https://example.com"
    assert data["url"]["title"] == "Example"
    assert len(data["chunks"]) == 0


def test_get_url_with_chunks_success(setup_url_deps: URLDepsSetup):
    """Test GET /urls/{url_id} returns URL with all chunks ordered by chunk_order."""
    url_repo, chunk_repo, _ = setup_url_deps()

    # Create URL
    url = url_repo.add(URLCreate(url="https://example.com", title="Example"))

    # Add chunks in non-sequential order to verify ordering
    chunk_repo.add(
        URLChunkCreate(
            content="Content 2",
            content_hash="hash2",
            url_id=url.id,
            chunk_order=2,
            is_summary=False,
            embedding=[0.2] * 1536,
        )
    )
    chunk_repo.add(
        URLChunkCreate(
            content="Summary",
            content_hash="hash0",
            url_id=url.id,
            chunk_order=0,
            is_summary=True,
            embedding=[0.0] * 1536,
        )
    )
    chunk_repo.add(
        URLChunkCreate(
            content="Content 1",
            content_hash="hash1",
            url_id=url.id,
            chunk_order=1,
            is_summary=False,
            embedding=[0.1] * 1536,
        )
    )

    response = client.get(f"/urls/{url.id}")

    assert response.status_code == 200
    data = response.json()

    # Verify URL metadata
    assert data["url"]["id"] == url.id
    assert data["url"]["url"] == "https://example.com"
    assert data["url"]["title"] == "Example"

    # Verify chunks are returned and ordered by chunk_order
    assert len(data["chunks"]) == 3
    assert data["chunks"][0]["chunk_order"] == 0
    assert data["chunks"][0]["is_summary"] is True
    assert data["chunks"][0]["content"] == "Summary"

    assert data["chunks"][1]["chunk_order"] == 1
    assert data["chunks"][1]["is_summary"] is False
    assert data["chunks"][1]["content"] == "Content 1"

    assert data["chunks"][2]["chunk_order"] == 2
    assert data["chunks"][2]["is_summary"] is False
    assert data["chunks"][2]["content"] == "Content 2"


def test_get_chunk_with_context_stream_chunk_not_found(setup_url_deps: URLDepsSetup):
    """Test GET /urls/{url_id}/chunks/{chunk_id} returns 404 when chunk not found."""
    setup_url_deps()

    response = client.get("/urls/999/chunks/999")

    assert response.status_code == 404
    data = response.json()
    assert "Chunk not found" in data["detail"]


def test_get_chunk_with_context_stream_url_not_found(setup_url_deps: URLDepsSetup):
    """Test 404 when URL doesn't exist (chunk URL ID mismatch)."""
    url_repo, chunk_repo, _ = setup_url_deps()

    # Create URL and chunk, then try with wrong URL ID
    url = url_repo.add(URLCreate(url="https://example.com", title="Example"))
    chunk = chunk_repo.add(
        URLChunkCreate(
            content="Test",
            content_hash="hash1",
            url_id=url.id,
            chunk_order=0,
            is_summary=True,
            embedding=[0.1] * 1536,
        )
    )

    # Request with wrong URL ID - chunk won't be found with url_id=999
    response = client.get(f"/urls/999/chunks/{chunk.id}")

    assert response.status_code == 404
    # Chunk lookup fails first because url_id doesn't match
    data = response.json()
    assert "Chunk not found" in data["detail"] or "URL not found" in data["detail"]


def test_get_chunk_with_context_stream_success(setup_url_deps: URLDepsSetup):
    """Test GET /urls/{url_id}/chunks/{chunk_id} streams events correctly."""
    url_repo, chunk_repo, _ = setup_url_deps()

    # Create test URL and chunk
    url = url_repo.add(URLCreate(url="https://example.com", title="Example"))
    chunk = chunk_repo.add(
        URLChunkCreate(
            content="Test chunk content",
            content_hash="hash1",
            url_id=url.id,
            chunk_order=1,
            is_summary=False,
            embedding=[0.1] * 1536,
        )
    )

    # Make SSE request
    response = client.get(f"/urls/{url.id}/chunks/{chunk.id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Parse SSE events
    events = []
    for line in response.iter_lines():
        if line.startswith("event:"):
            events.append(line.split(":", 1)[1].strip())

    # Verify event sequence
    assert "metadata" in events
    assert "context_chunk" in events  # At least one context chunk
    assert "context_complete" in events
