"""
Tests for URLChunkRepository methods using in-memory database.
"""

import pytest
from sqlmodel import Session

from .url_repository import URLRepository
from .urlchunk_repository import URLChunkRepository
from src.repositories.models import URLCreate, URLChunkCreate, URLChunkRead


@pytest.fixture(name="sample_url_id")
def sample_url_id_fixture(url_repo: URLRepository) -> int:
    """Create a sample URL and return its ID."""
    url = URLCreate(url="https://example.com/article", title="Test Article")
    url = url_repo.add(url)
    return url.id


@pytest.fixture(name="sample_chunks")
def sample_chunks_fixture(
    urlchunk_repo: URLChunkRepository, sample_url_id: int
) -> list[URLChunkRead]:
    """Create sample URL chunks and return them as URLChunkRead objects."""
    # Create a sample embedding (realistic production data)
    embedding = [0.1] * 1536

    chunks = [
        URLChunkCreate(
            content="First chunk content",
            content_hash="hash1",
            url_id=sample_url_id,
            chunk_order=0,
            is_summary=True,
            embedding=embedding,
        ),
        URLChunkCreate(
            content="Second chunk content",
            content_hash="hash2",
            url_id=sample_url_id,
            chunk_order=1,
            is_summary=False,
            embedding=embedding,
        ),
        URLChunkCreate(
            content="Third chunk content",
            content_hash="hash3",
            url_id=sample_url_id,
            chunk_order=2,
            is_summary=False,
            embedding=embedding,
        ),
    ]
    added_chunks: list[URLChunkRead] = []
    for chunk in chunks:
        added_chunks.append(urlchunk_repo.add(chunk))

    return added_chunks


def test_add_new_chunk(urlchunk_repo: URLChunkRepository, sample_url_id: int):
    """Test adding a new URL chunk."""
    new_chunk = URLChunkCreate(
        content="New test chunk",
        content_hash="unique_hash_123",
        url_id=sample_url_id,
        chunk_order=0,
        is_summary=True,
    )

    result = urlchunk_repo.add(new_chunk)

    assert result.id is not None
    assert result.content == "New test chunk"
    assert result.content_hash == "unique_hash_123"
    assert result.url_id == sample_url_id
    assert result.chunk_order == 0
    assert result.is_summary is True


def test_add_duplicate_hash_returns_existing(
    urlchunk_repo: URLChunkRepository, sample_url_id: int
):
    """Test that adding a chunk with duplicate content hash returns the existing chunk."""

    # Add first chunk
    first_chunk = URLChunkCreate(
        content="First chunk",
        content_hash="duplicate_hash",
        url_id=sample_url_id,
        chunk_order=0,
        is_summary=True,
    )
    result1 = urlchunk_repo.add(first_chunk)

    # Try to add second chunk with same content hash but different content
    second_chunk = URLChunkCreate(
        content="Different content",
        content_hash="duplicate_hash",
        url_id=sample_url_id,
        chunk_order=1,
        is_summary=False,
    )
    result2 = urlchunk_repo.add(second_chunk)

    # Should return the same chunk
    assert result1.id == result2.id
    assert result2.content == "First chunk"  # Original content preserved
    assert result2.is_summary is True  # Original values preserved


def test_get_existing_chunk(
    urlchunk_repo: URLChunkRepository,
    sample_chunks: list[URLChunkRead],
    sample_url_id: int,
):
    """Test getting a chunk by ID and URL ID when it exists."""
    chunk = sample_chunks[0]

    result = urlchunk_repo.get(chunk.id, sample_url_id)

    assert result is not None
    assert result.id == chunk.id
    assert result.content == "First chunk content"
    assert result.url_id == sample_url_id


def test_get_chunk_wrong_url_id(
    urlchunk_repo: URLChunkRepository, sample_chunks: list[URLChunkRead]
):
    """Test getting a chunk with wrong URL ID returns None."""
    chunk = sample_chunks[0]

    result = urlchunk_repo.get(chunk.id, 999)

    assert result is None


def test_get_by_id_success(
    urlchunk_repo: URLChunkRepository, sample_chunks: list[URLChunkRead]
):
    """Test getting a chunk by ID when it exists."""
    result = urlchunk_repo.get_by_id(sample_chunks[0].id)

    assert result is not None
    assert result.id == sample_chunks[0].id
    assert result.content == "First chunk content"
    assert result.content_hash == "hash1"
    assert result.url_id == sample_chunks[0].url_id


def test_get_by_id_not_found(urlchunk_repo: URLChunkRepository):
    """Test getting a chunk by ID when it doesn't exist."""
    result = urlchunk_repo.get_by_id(999)
    assert result is None


def test_get_by_url_id(
    urlchunk_repo: URLChunkRepository,
    url_repo: URLRepository,
    sample_chunks: list[URLChunkRead],
    sample_url_id: int,
):
    """Test getting chunks by URL ID."""
    # Create a second URL with its own chunk
    url2 = URLCreate(url="https://example.com/another", title="Another Article")
    url2 = url_repo.add(url2)

    chunk_url2 = URLChunkCreate(
        content="URL 2 Chunk 1",
        content_hash="u2c1",
        url_id=url2.id,
        chunk_order=0,
        is_summary=True,
    )
    urlchunk_repo.add(chunk_url2)

    # Get chunks for first URL (should return sample_chunks)
    url1_chunks = urlchunk_repo.get_by_url_id(sample_url_id)
    assert len(url1_chunks) == 3  # sample_chunks has 3 chunks
    contents = [chunk.content for chunk in url1_chunks]
    assert "First chunk content" in contents
    assert "Second chunk content" in contents
    assert "Third chunk content" in contents

    # Verify chunks are ordered by chunk_order
    assert url1_chunks[0].chunk_order == 0
    assert url1_chunks[1].chunk_order == 1
    assert url1_chunks[2].chunk_order == 2

    # Get chunks for second URL
    url2_chunks = urlchunk_repo.get_by_url_id(url2.id)
    assert len(url2_chunks) == 1
    assert url2_chunks[0].content == "URL 2 Chunk 1"


def test_get_by_url_id_empty(urlchunk_repo: URLChunkRepository):
    """Test getting chunks by URL ID when no chunks exist."""
    chunks = urlchunk_repo.get_by_url_id(999)
    assert chunks == []


def test_get_random(
    urlchunk_repo: URLChunkRepository, sample_chunks: list[URLChunkRead]
):
    """Test getting a random chunk."""
    random_chunk = urlchunk_repo.get_random()

    assert random_chunk is not None
    assert random_chunk.id in [chunk.id for chunk in sample_chunks]


def test_get_random_empty(urlchunk_repo: URLChunkRepository):
    """Test getting a random chunk when database is empty."""
    random_chunk = urlchunk_repo.get_random()
    assert random_chunk is None


def test_find_similar_chunks_no_embedding(
    urlchunk_repo: URLChunkRepository, session: Session, sample_url_id: int
):
    """Test find_similar_chunks when the chunk has no embedding."""
    chunk = URLChunkCreate(
        content="No embedding",
        content_hash="no_embed",
        url_id=sample_url_id,
        chunk_order=0,
        is_summary=False,
        embedding=None,
    )
    chunk_read = urlchunk_repo.add(chunk)

    similar = urlchunk_repo.find_similar_chunks(chunk_read, limit=5)
    assert similar == []


def test_get_chunk_counts_by_url_ids(
    urlchunk_repo: URLChunkRepository,
    url_repo: URLRepository,
    sample_chunks: list[URLChunkRead],
    sample_url_id: int,
):
    """Test getting chunk counts for multiple URLs."""
    # sample_chunks fixture creates 3 chunks for sample_url_id
    # Create additional URLs
    url2 = URLCreate(url="https://example.com/url2", title="URL 2")
    url3 = URLCreate(url="https://example.com/url3", title="URL 3")
    url2 = url_repo.add(url2)
    url3 = url_repo.add(url3)

    # Add chunks to url2 (url1 already has 3 from fixture)
    chunk4 = URLChunkCreate(
        content="U2 C1",
        content_hash="u2c1_count",
        url_id=url2.id,
        chunk_order=0,
        is_summary=True,
    )
    chunk5 = URLChunkCreate(
        content="U2 C2",
        content_hash="u2c2_count",
        url_id=url2.id,
        chunk_order=1,
        is_summary=False,
    )
    # URL 3 has no chunks

    urlchunk_repo.add(chunk4)
    urlchunk_repo.add(chunk5)

    # Get counts for all URLs
    counts = urlchunk_repo.get_chunk_counts_by_url_ids(
        [sample_url_id, url2.id, url3.id]
    )

    assert counts[sample_url_id] == 3  # From sample_chunks fixture
    assert counts[url2.id] == 2
    # URL 3 should not appear in results (no chunks)
    assert url3.id not in counts


def test_get_chunk_counts_by_url_ids_empty_list(urlchunk_repo: URLChunkRepository):
    """Test getting chunk counts with empty URL ID list."""
    counts = urlchunk_repo.get_chunk_counts_by_url_ids([])
    assert counts == {}


def test_get_chunk_counts_by_url_ids_nonexistent_urls(
    urlchunk_repo: URLChunkRepository,
):
    """Test getting chunk counts for URLs that don't exist."""
    counts = urlchunk_repo.get_chunk_counts_by_url_ids([999, 1000])
    assert counts == {}


def test_count_with_embeddings(
    urlchunk_repo: URLChunkRepository,
    sample_chunks: list[URLChunkRead],
    sample_url_id: int,
):
    """Test counting chunks with embeddings in a mixed scenario."""
    # sample_chunks has 3 chunks with embeddings
    # Add 1 chunk WITHOUT embedding to test mixed scenario
    urlchunk_repo.add(
        URLChunkCreate(
            content="Without embedding",
            content_hash="no_emb",
            url_id=sample_url_id,
            chunk_order=3,
            is_summary=False,
            embedding=None,
        )
    )

    # Should only count the 3 from sample_chunks (not the one without embedding)
    count = urlchunk_repo.count_with_embeddings()
    assert count == 3


def test_count_with_embeddings_empty(urlchunk_repo: URLChunkRepository):
    """Test counting chunks with embeddings when none exist."""
    count = urlchunk_repo.count_with_embeddings()
    assert count == 0


def test_count_with_embeddings_all_have_embeddings(
    urlchunk_repo: URLChunkRepository, sample_chunks: list[URLChunkRead]
):
    """Test counting chunks when all have embeddings."""
    # sample_chunks fixture creates 3 chunks, all with embeddings
    count = urlchunk_repo.count_with_embeddings()
    assert count == 3
