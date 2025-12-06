"""
Tests for NoteRepository methods using in-memory database.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine
from .note_repository import NoteRepository
from .models import Note, Book


@pytest.fixture(name="session")
def session_fixture():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="sample_book")
def sample_book_fixture(session: Session):
    """Create a sample book for testing."""
    book = Book(title="Test Book", author="Test Author")
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


@pytest.fixture(name="sample_notes")
def sample_notes_fixture(session: Session, sample_book: Book):
    """Create sample notes for testing."""
    assert sample_book.id is not None
    notes = [
        Note(
            content="First note content",
            content_hash="hash1",
            book_id=sample_book.id,
        ),
        Note(
            content="Second note content",
            content_hash="hash2",
            book_id=sample_book.id,
        ),
        Note(
            content="Third note content",
            content_hash="hash3",
            book_id=sample_book.id,
        ),
    ]
    for note in notes:
        session.add(note)
    session.commit()
    for note in notes:
        session.refresh(note)
        assert note.id is not None
    return notes


def test_get_by_id_success(session: Session, sample_notes: list[Note]):
    """Test getting a note by ID when it exists."""
    repo = NoteRepository(session)

    # Get the first note by ID
    assert sample_notes[0].id is not None
    result = repo.get_by_id(sample_notes[0].id)

    assert result is not None
    assert result.id == sample_notes[0].id
    assert result.content == "First note content"
    assert result.content_hash == "hash1"
    assert result.book_id == sample_notes[0].book_id


def test_get_by_id_not_found(session: Session):
    """Test getting a note by ID when it doesn't exist."""
    repo = NoteRepository(session)

    # Try to get a note with non-existent ID
    result = repo.get_by_id(999)

    assert result is None


def test_get_by_id_multiple_books(session: Session):
    """Test get_by_id retrieves note regardless of book."""
    # Create two books
    book1 = Book(title="Book 1", author="Author 1")
    book2 = Book(title="Book 2", author="Author 2")
    session.add(book1)
    session.add(book2)
    session.commit()
    session.refresh(book1)
    session.refresh(book2)
    assert book1.id is not None
    assert book2.id is not None

    # Create notes in different books
    note1 = Note(content="Note in book 1", content_hash="hash_b1", book_id=book1.id)
    note2 = Note(content="Note in book 2", content_hash="hash_b2", book_id=book2.id)
    session.add(note1)
    session.add(note2)
    session.commit()
    session.refresh(note1)
    session.refresh(note2)
    assert note1.id is not None
    assert note2.id is not None

    repo = NoteRepository(session)

    # get_by_id should find note1 without needing book_id
    result1 = repo.get_by_id(note1.id)
    assert result1 is not None
    assert result1.id == note1.id
    assert result1.book_id == book1.id

    # get_by_id should find note2 without needing book_id
    result2 = repo.get_by_id(note2.id)
    assert result2 is not None
    assert result2.id == note2.id
    assert result2.book_id == book2.id


def test_get_vs_get_by_id(session: Session, sample_book: Book):
    """Test that get() and get_by_id() differ in their requirements."""
    assert sample_book.id is not None
    # Create a note
    note = Note(
        content="Test note",
        content_hash="test_hash",
        book_id=sample_book.id,
    )
    session.add(note)
    session.commit()
    session.refresh(note)
    assert note.id is not None

    repo = NoteRepository(session)

    # get() requires both note_id and book_id
    result_get = repo.get(note.id, sample_book.id)
    assert result_get is not None
    assert result_get.id == note.id

    # get() returns None if book_id doesn't match
    result_wrong_book = repo.get(note.id, 999)
    assert result_wrong_book is None

    # get_by_id() only requires note_id and ignores book
    result_get_by_id = repo.get_by_id(note.id)
    assert result_get_by_id is not None
    assert result_get_by_id.id == note.id
    assert result_get_by_id.book_id == sample_book.id


def test_get_by_id_returns_note_read(session: Session, sample_notes: list[Note]):
    """Test that get_by_id returns NoteRead with all required fields."""
    repo = NoteRepository(session)

    assert sample_notes[1].id is not None
    result = repo.get_by_id(sample_notes[1].id)

    assert result is not None
    # NoteRead should have id, content, content_hash, book_id, embedding, created_at
    assert hasattr(result, "id")
    assert hasattr(result, "content")
    assert hasattr(result, "content_hash")
    assert hasattr(result, "book_id")
    assert hasattr(result, "embedding")
    assert hasattr(result, "created_at")

    # Verify the values match
    assert result.id == sample_notes[1].id
    assert result.content == "Second note content"
    assert result.content_hash == "hash2"
    assert result.created_at is not None
