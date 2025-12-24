"""
Tests for NoteRepository methods using in-memory database.
"""

import pytest
from sqlmodel import Session

from .book_repository import BookRepository
from .note_repository import NoteRepository
from .models import BookCreate, NoteCreate, NoteRead


@pytest.fixture(name="sample_book_id")
def sample_book_id_fixture(book_repo: BookRepository) -> int:
    """Create a sample book and return its ID."""
    book = BookCreate(title="Test Book", author="Test Author")
    book = book_repo.add(book)
    assert book.id is not None
    return book.id


@pytest.fixture(name="sample_notes")
def sample_notes_fixture(
    note_repo: NoteRepository, sample_book_id: int
) -> list[NoteRead]:
    """Create sample notes and return them as NoteRead objects."""
    notes = [
        NoteCreate(
            content="First note content",
            content_hash="hash1",
            book_id=sample_book_id,
        ),
        NoteCreate(
            content="Second note content",
            content_hash="hash2",
            book_id=sample_book_id,
        ),
        NoteCreate(
            content="Third note content",
            content_hash="hash3",
            book_id=sample_book_id,
        ),
    ]
    for note in notes:
        note_repo.add(note)

    return note_repo.list_notes()


def test_get_by_id_success(note_repo: NoteRepository, sample_notes: list[NoteRead]):
    """Test getting a note by ID when it exists."""
    # Get the first note by ID
    result = note_repo.get_by_id(sample_notes[0].id)

    assert result is not None
    assert result.id == sample_notes[0].id
    assert result.content == "First note content"
    assert result.content_hash == "hash1"
    assert result.book_id == sample_notes[0].book_id


def test_get_by_id_not_found(note_repo: NoteRepository):
    """Test getting a note by ID when it doesn't exist."""
    result = note_repo.get_by_id(999)
    assert result is None


def test_add_new_note(note_repo: NoteRepository, sample_book_id: int):
    """Test adding a new note."""
    new_note = NoteCreate(
        content="New test note",
        content_hash="unique_hash_123",
        book_id=sample_book_id,
    )

    result = note_repo.add(new_note)

    assert result.id is not None
    assert result.content == "New test note"
    assert result.content_hash == "unique_hash_123"
    assert result.book_id == sample_book_id


def test_add_duplicate_hash_returns_existing(
    note_repo: NoteRepository, sample_book_id: int
):
    """Test that adding a note with duplicate content hash returns the existing note."""

    # Add first note
    first_note = NoteCreate(
        content="First note",
        content_hash="duplicate_hash",
        book_id=sample_book_id,
    )
    result1 = note_repo.add(first_note)

    # Try to add second note with same content hash but different content
    second_note = NoteCreate(
        content="Different content",
        content_hash="duplicate_hash",
        book_id=sample_book_id,
    )
    result2 = note_repo.add(second_note)

    # Should return the same note
    assert result1.id == result2.id
    assert result2.content == "First note"  # Original content preserved

    # Verify only one note exists
    all_notes = note_repo.list_notes()
    matching_notes = [n for n in all_notes if n.content_hash == "duplicate_hash"]
    assert len(matching_notes) == 1


def test_list_notes(note_repo: NoteRepository, sample_notes: list[NoteRead]):
    """Test listing all notes."""
    notes = note_repo.list_notes()

    assert len(notes) == 3
    contents = [note.content for note in notes]
    assert "First note content" in contents
    assert "Second note content" in contents
    assert "Third note content" in contents


def test_list_notes_empty(note_repo: NoteRepository):
    """Test listing notes when database is empty."""
    notes = note_repo.list_notes()
    assert notes == []


def test_get_by_book_id(
    note_repo: NoteRepository, book_repo: BookRepository, sample_book_id: int
):
    """Test getting notes by book ID."""
    # Create a second book
    book2 = BookCreate(title="Another Book", author="Another Author")
    book2 = book_repo.add(book2)
    assert book2.id is not None

    # Add notes to both books
    note1 = NoteCreate(
        content="Book 1 Note 1", content_hash="b1n1", book_id=sample_book_id
    )
    note2 = NoteCreate(
        content="Book 1 Note 2", content_hash="b1n2", book_id=sample_book_id
    )
    note3 = NoteCreate(content="Book 2 Note 1", content_hash="b2n1", book_id=book2.id)
    for n in [note1, note2, note3]:
        note_repo.add(n)

    # Get notes for first book
    book1_notes = note_repo.get_by_book_id(sample_book_id)
    assert len(book1_notes) == 2
    contents = [note.content for note in book1_notes]
    assert "Book 1 Note 1" in contents
    assert "Book 1 Note 2" in contents

    # Get notes for second book
    book2_notes = note_repo.get_by_book_id(book2.id)
    assert len(book2_notes) == 1
    assert book2_notes[0].content == "Book 2 Note 1"


def test_get_by_book_id_empty(note_repo: NoteRepository):
    """Test getting notes by book ID when no notes exist."""
    notes = note_repo.get_by_book_id(999)
    assert notes == []


def test_delete_existing_note(note_repo: NoteRepository, sample_notes: list[NoteRead]):
    """Test deleting an existing note."""
    note_id = sample_notes[0].id

    # Verify note exists
    assert note_repo.get_by_id(note_id) is not None

    # Delete note
    note_repo.delete(note_id)

    # Verify note no longer exists
    assert note_repo.get_by_id(note_id) is None

    # Verify other notes still exist
    remaining_notes = note_repo.list_notes()
    assert len(remaining_notes) == 2


def test_delete_nonexistent_note(note_repo: NoteRepository):
    """Test deleting a note that doesn't exist (should not raise error)."""
    # Should not raise an error
    note_repo.delete(999)


def test_get_random(note_repo: NoteRepository, sample_notes: list[NoteRead]):
    """Test getting a random note."""
    random_note = note_repo.get_random()

    assert random_note is not None
    assert random_note.id in [note.id for note in sample_notes]


def test_get_random_empty(note_repo: NoteRepository):
    """Test getting a random note when database is empty."""
    random_note = note_repo.get_random()
    assert random_note is None


def test_find_similar_notes_no_embedding(
    note_repo: NoteRepository, session: Session, sample_book_id: int
):
    """Test find_similar_notes when the note has no embedding."""
    note = NoteCreate(
        content="No embedding",
        content_hash="no_embed",
        book_id=sample_book_id,
        embedding=None,
    )
    note_read = note_repo.add(note)

    similar = note_repo.find_similar_notes(note_read, limit=5)
    assert similar == []


def test_get_note_counts_by_book_ids(
    note_repo: NoteRepository, book_repo: BookRepository, sample_book_id: int
):
    """Test getting note counts for multiple books."""
    # Create a second book
    book2 = BookCreate(title="Book 2", author="Author 2")
    book3 = BookCreate(title="Book 3", author="Author 3")
    book2 = book_repo.add(book2)
    book3 = book_repo.add(book3)
    assert book2.id is not None
    assert book3.id is not None

    # Add notes to books
    note1 = NoteCreate(
        content="B1 N1", content_hash="b1n1_count", book_id=sample_book_id
    )
    note2 = NoteCreate(
        content="B1 N2", content_hash="b1n2_count", book_id=sample_book_id
    )
    note3 = NoteCreate(
        content="B1 N3", content_hash="b1n3_count", book_id=sample_book_id
    )
    note4 = NoteCreate(content="B2 N1", content_hash="b2n1_count", book_id=book2.id)
    note5 = NoteCreate(content="B2 N2", content_hash="b2n2_count", book_id=book2.id)
    # Book 3 has no notes

    for n in [note1, note2, note3, note4, note5]:
        note_repo.add(n)

    # Get counts for all books
    counts = note_repo.get_note_counts_by_book_ids([sample_book_id, book2.id, book3.id])

    assert counts[sample_book_id] == 3
    assert counts[book2.id] == 2
    # Book 3 should not appear in results (no notes)
    assert book3.id not in counts


def test_get_note_counts_by_book_ids_empty_list(note_repo: NoteRepository):
    """Test getting note counts with empty book ID list."""
    counts = note_repo.get_note_counts_by_book_ids([])
    assert counts == {}


def test_get_note_counts_by_book_ids_nonexistent_books(note_repo: NoteRepository):
    """Test getting note counts for books that don't exist."""
    counts = note_repo.get_note_counts_by_book_ids([999, 1000])
    assert counts == {}
