"""
Tests for NoteRepository methods using in-memory database.
"""

import pytest
from sqlmodel import Session
from .note_repository import NoteRepository
from .models import Book, NoteCreate, NoteRead


@pytest.fixture(name="sample_book_id")
def sample_book_id_fixture(session: Session) -> int:
    """Create a sample book and return its ID."""
    book = Book(title="Test Book", author="Test Author")
    session.add(book)
    session.commit()
    session.refresh(book)
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


def test_get_vs_get_by_id(
    note_repo: NoteRepository, sample_notes: list[NoteRead], sample_book_id: int
):
    """Test that get() and get_by_id() differ in their requirements."""
    note = sample_notes[0]

    # get() requires both note_id and book_id
    result_get = note_repo.get(note.id, sample_book_id)
    assert result_get is not None
    assert result_get.id == note.id

    # get() returns None if book_id doesn't match
    result_wrong_book = note_repo.get(note.id, 999)
    assert result_wrong_book is None

    # get_by_id() only requires note_id and ignores book
    result_get_by_id = note_repo.get_by_id(note.id)
    assert result_get_by_id is not None
    assert result_get_by_id.id == note.id
    assert result_get_by_id.book_id == sample_book_id
