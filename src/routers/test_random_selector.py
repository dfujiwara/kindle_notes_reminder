"""
Tests for the random content selector.

Tests weighted random selection between notes and URL chunks.
"""

from datetime import datetime, timezone

from src.routers.random_selector import (
    RandomNoteSelection,
    RandomChunkSelection,
    select_random_content,
)
from src.repositories.models import NoteRead, NoteCreate, URLChunkRead, URLChunkCreate
from src.test_utils import StubNoteRepository, StubURLChunkRepository


def test_select_random_content_empty_database():
    """Test that None is returned when no content exists."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()

    result = select_random_content(note_repo, chunk_repo)
    assert result is None


def test_select_random_content_only_notes():
    """Test selection when only notes exist."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()

    # Add notes with embeddings
    for i in range(5):
        note = note_repo.add(
            NoteCreate(
                book_id=1,
                content=f"Note {i} content",
                content_hash=f"hash_{i}",
                embedding=[0.1] * 1536,
            )
        )

    result = select_random_content(note_repo, chunk_repo)

    assert result is not None
    assert isinstance(result, RandomNoteSelection)
    assert result.content_type == "note"
    assert result.item.book_id == 1


def test_select_random_content_only_chunks():
    """Test selection when only chunks exist."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()

    # Add chunks with embeddings
    for i in range(5):
        chunk = chunk_repo.add(
            URLChunkCreate(
                url_id=1,
                content=f"Chunk {i} content",
                content_hash=f"chunk_hash_{i}",
                chunk_order=i,
                is_summary=False,
                embedding=[0.2] * 1536,
            )
        )

    result = select_random_content(note_repo, chunk_repo)

    assert result is not None
    assert isinstance(result, RandomChunkSelection)
    assert result.content_type == "url_chunk"
    assert result.item.url_id == 1


def test_select_random_content_both_types():
    """Test selection when both notes and chunks exist."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()

    # Add notes
    for i in range(10):
        note_repo.add(
            NoteCreate(
                book_id=1,
                content=f"Note {i}",
                content_hash=f"note_hash_{i}",
                embedding=[0.1] * 1536,
            )
        )

    # Add chunks
    for i in range(10):
        chunk_repo.add(
            URLChunkCreate(
                url_id=1,
                content=f"Chunk {i}",
                content_hash=f"chunk_hash_{i}",
                chunk_order=i,
                is_summary=False,
                embedding=[0.2] * 1536,
            )
        )

    # With equal counts, we should eventually get both types
    results = []
    for _ in range(20):
        result = select_random_content(note_repo, chunk_repo)
        results.append(result)

    # Verify we got both types
    has_note = any(isinstance(r, RandomNoteSelection) for r in results)
    has_chunk = any(isinstance(r, RandomChunkSelection) for r in results)

    assert has_note, "Expected at least one note selection"
    assert has_chunk, "Expected at least one chunk selection"


def test_select_random_content_weighted_distribution():
    """Test that distribution is roughly proportional to counts."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()

    # Add 3 notes with embeddings
    for i in range(3):
        note_repo.add(
            NoteCreate(
                book_id=1,
                content=f"Note {i}",
                content_hash=f"note_hash_{i}",
                embedding=[0.1] * 1536,
            )
        )

    # Add 1 chunk with embeddings
    chunk_repo.add(
        URLChunkCreate(
            url_id=1,
            content="Chunk",
            content_hash="chunk_hash_0",
            chunk_order=0,
            is_summary=False,
            embedding=[0.2] * 1536,
        )
    )

    note_count = 0
    chunk_count = 0

    # Run many times to check distribution
    for _ in range(100):
        result = select_random_content(note_repo, chunk_repo)
        if isinstance(result, RandomNoteSelection):
            note_count += 1
        elif isinstance(result, RandomChunkSelection):
            chunk_count += 1

    # With 3:1 ratio, expect roughly 75% notes, 25% chunks
    # Allow some variance (40-85% for notes)
    assert 40 <= note_count <= 85, f"Expected ~75 notes, got {note_count}"
    assert 15 <= chunk_count <= 60, f"Expected ~25 chunks, got {chunk_count}"


def test_select_random_content_items_without_embeddings_excluded():
    """Test that items without embeddings are not counted."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()

    # Add notes without embeddings (embedding=None)
    note_repo.add(
        NoteCreate(
            book_id=1,
            content="Note without embedding",
            content_hash="no_embedding_hash",
            embedding=None,
        )
    )

    # Add notes with embeddings
    note_repo.add(
        NoteCreate(
            book_id=1,
            content="Note with embedding",
            content_hash="with_embedding_hash",
            embedding=[0.1] * 1536,
        )
    )

    # Should only count the one with embedding
    assert note_repo.count_with_embeddings() == 1

    result = select_random_content(note_repo, chunk_repo)
    assert result is not None
    assert isinstance(result, RandomNoteSelection)


def test_select_random_content_type_discrimination():
    """Test that content_type field correctly discriminates types."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()

    # Add multiple notes and chunks
    for i in range(10):
        note_repo.add(
            NoteCreate(
                book_id=1,
                content=f"Note {i}",
                content_hash=f"note_{i}",
                embedding=[0.1] * 1536,
            )
        )
        chunk_repo.add(
            URLChunkCreate(
                url_id=1,
                content=f"Chunk {i}",
                content_hash=f"chunk_{i}",
                chunk_order=i,
                is_summary=False,
                embedding=[0.2] * 1536,
            )
        )

    for _ in range(50):
        result = select_random_content(note_repo, chunk_repo)
        if result:
            if result.content_type == "note":
                assert isinstance(result, RandomNoteSelection)
                assert isinstance(result.item, NoteRead)
            elif result.content_type == "url_chunk":
                assert isinstance(result, RandomChunkSelection)
                assert isinstance(result.item, URLChunkRead)
