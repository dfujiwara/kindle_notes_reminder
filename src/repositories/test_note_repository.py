"""
Tests for NoteRepository methods using in-memory database.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine
from .note_repository import NoteRepository
from .models import Note, Book, NoteRead


@pytest.fixture(name="session")
def session_fixture():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


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
def sample_notes_fixture(session: Session, sample_book_id: int) -> list[NoteRead]:
    """Create sample notes and return them as NoteRead objects."""
    notes = [
        Note(
            content="First note content",
            content_hash="hash1",
            book_id=sample_book_id,
        ),
        Note(
            content="Second note content",
            content_hash="hash2",
            book_id=sample_book_id,
        ),
        Note(
            content="Third note content",
            content_hash="hash3",
            book_id=sample_book_id,
        ),
    ]
    for note in notes:
        session.add(note)
    session.commit()

    # Return NoteRead objects instead of Note objects
    repo = NoteRepository(session)
    return repo.list_notes()


def test_get_by_id_success(session: Session, sample_notes: list[NoteRead]):
    """Test getting a note by ID when it exists."""
    repo = NoteRepository(session)

    # Get the first note by ID
    result = repo.get_by_id(sample_notes[0].id)

    assert result is not None
    assert result.id == sample_notes[0].id
    assert result.content == "First note content"
    assert result.content_hash == "hash1"
    assert result.book_id == sample_notes[0].book_id


def test_get_by_id_not_found(session: Session):
    """Test getting a note by ID when it doesn't exist."""
    repo = NoteRepository(session)
    result = repo.get_by_id(999)
    assert result is None


def test_get_vs_get_by_id(
    session: Session, sample_notes: list[NoteRead], sample_book_id: int
):
    """Test that get() and get_by_id() differ in their requirements."""
    repo = NoteRepository(session)
    note = sample_notes[0]

    # get() requires both note_id and book_id
    result_get = repo.get(note.id, sample_book_id)
    assert result_get is not None
    assert result_get.id == note.id

    # get() returns None if book_id doesn't match
    result_wrong_book = repo.get(note.id, 999)
    assert result_wrong_book is None

    # get_by_id() only requires note_id and ignores book
    result_get_by_id = repo.get_by_id(note.id)
    assert result_get_by_id is not None
    assert result_get_by_id.id == note.id
    assert result_get_by_id.book_id == sample_book_id
