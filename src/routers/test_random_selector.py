"""
Tests for the random content selector.

Tests weighted random selection between notes and URL chunks.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.routers.random_selector import (
    RandomNoteSelection,
    RandomChunkSelection,
    select_random_content,
)
from src.repositories.models import NoteRead, URLChunkRead


def test_select_random_content_empty_database():
    """Test that None is returned when no content exists."""
    note_repo = MagicMock()
    chunk_repo = MagicMock()

    note_repo.count_with_embeddings.return_value = 0
    chunk_repo.count_with_embeddings.return_value = 0

    result = select_random_content(note_repo, chunk_repo)
    assert result is None


def _create_test_note() -> NoteRead:
    """Create a test note with embeddings."""
    return NoteRead(
        id=1,
        book_id=1,
        content="Test note content",
        content_hash="test_hash_1",
        embedding=[0.1] * 1536,
        created_at=datetime.now(timezone.utc),
    )


def _create_test_chunk() -> URLChunkRead:
    """Create a test URL chunk with embeddings."""
    return URLChunkRead(
        id=1,
        url_id=1,
        content="Test chunk content",
        content_hash="test_chunk_hash_1",
        chunk_order=1,
        is_summary=False,
        embedding=[0.2] * 1536,
        created_at=datetime.now(timezone.utc),
    )


def test_select_random_content_only_notes():
    """Test selection when only notes exist."""
    note = _create_test_note()
    note_repo = MagicMock()
    chunk_repo = MagicMock()

    note_repo.count_with_embeddings.return_value = 5
    chunk_repo.count_with_embeddings.return_value = 0
    note_repo.get_random.return_value = note

    result = select_random_content(note_repo, chunk_repo)

    assert result is not None
    assert isinstance(result, RandomNoteSelection)
    assert result.content_type == "note"
    assert result.item == note
    note_repo.get_random.assert_called_once()
    chunk_repo.get_random.assert_not_called()


def test_select_random_content_only_chunks():
    """Test selection when only chunks exist."""
    chunk = _create_test_chunk()
    note_repo = MagicMock()
    chunk_repo = MagicMock()

    note_repo.count_with_embeddings.return_value = 0
    chunk_repo.count_with_embeddings.return_value = 5
    chunk_repo.get_random.return_value = chunk

    result = select_random_content(note_repo, chunk_repo)

    assert result is not None
    assert isinstance(result, RandomChunkSelection)
    assert result.content_type == "url_chunk"
    assert result.item == chunk
    chunk_repo.get_random.assert_called_once()
    note_repo.get_random.assert_not_called()


def test_select_random_content_both_types():
    """Test selection when both notes and chunks exist."""
    note = _create_test_note()
    chunk = _create_test_chunk()
    note_repo = MagicMock()
    chunk_repo = MagicMock()

    note_repo.count_with_embeddings.return_value = 10
    chunk_repo.count_with_embeddings.return_value = 10
    note_repo.get_random.return_value = note
    chunk_repo.get_random.return_value = chunk

    # With equal counts, we should eventually get both types
    # (though individual calls are random)
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
    note = _create_test_note()
    chunk = _create_test_chunk()
    note_repo = MagicMock()
    chunk_repo = MagicMock()

    # 3:1 ratio - notes are 3x more likely
    note_repo.count_with_embeddings.return_value = 3
    chunk_repo.count_with_embeddings.return_value = 1
    note_repo.get_random.return_value = note
    chunk_repo.get_random.return_value = chunk

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


def test_select_random_content_get_random_returns_none():
    """Test that None is returned if get_random() returns None."""
    note_repo = MagicMock()
    chunk_repo = MagicMock()

    note_repo.count_with_embeddings.return_value = 5
    chunk_repo.count_with_embeddings.return_value = 0
    note_repo.get_random.return_value = None

    result = select_random_content(note_repo, chunk_repo)
    assert result is None


def test_select_random_content_type_discrimination():
    """Test that content_type field correctly discriminates types."""
    note = _create_test_note()
    chunk = _create_test_chunk()
    note_repo = MagicMock()
    chunk_repo = MagicMock()

    note_repo.count_with_embeddings.return_value = 100
    chunk_repo.count_with_embeddings.return_value = 100
    note_repo.get_random.return_value = note
    chunk_repo.get_random.return_value = chunk

    for _ in range(50):
        result = select_random_content(note_repo, chunk_repo)
        if result:
            if result.content_type == "note":
                assert isinstance(result, RandomNoteSelection)
                assert isinstance(result.item, NoteRead)
            elif result.content_type == "url_chunk":
                assert isinstance(result, RandomChunkSelection)
                assert isinstance(result.item, URLChunkRead)
