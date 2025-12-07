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


def test_add_new_note(session: Session, sample_book_id: int):
    """Test adding a new note."""
    from .models import NoteCreate

    repo = NoteRepository(session)

    new_note = NoteCreate(
        content="New test note",
        content_hash="unique_hash_123",
        book_id=sample_book_id,
    )

    result = repo.add(new_note)

    assert result.id is not None
    assert result.content == "New test note"
    assert result.content_hash == "unique_hash_123"
    assert result.book_id == sample_book_id


def test_add_duplicate_hash_returns_existing(session: Session, sample_book_id: int):
    """Test that adding a note with duplicate content hash returns the existing note."""
    from .models import NoteCreate

    repo = NoteRepository(session)

    # Add first note
    first_note = NoteCreate(
        content="First note",
        content_hash="duplicate_hash",
        book_id=sample_book_id,
    )
    result1 = repo.add(first_note)

    # Try to add second note with same content hash but different content
    second_note = NoteCreate(
        content="Different content",
        content_hash="duplicate_hash",
        book_id=sample_book_id,
    )
    result2 = repo.add(second_note)

    # Should return the same note
    assert result1.id == result2.id
    assert result2.content == "First note"  # Original content preserved

    # Verify only one note exists
    all_notes = repo.list_notes()
    matching_notes = [n for n in all_notes if n.content_hash == "duplicate_hash"]
    assert len(matching_notes) == 1


def test_list_notes(session: Session, sample_notes: list[NoteRead]):
    """Test listing all notes."""
    repo = NoteRepository(session)
    notes = repo.list_notes()

    assert len(notes) == 3
    contents = [note.content for note in notes]
    assert "First note content" in contents
    assert "Second note content" in contents
    assert "Third note content" in contents


def test_list_notes_empty(session: Session):
    """Test listing notes when database is empty."""
    repo = NoteRepository(session)
    notes = repo.list_notes()
    assert notes == []


def test_get_by_book_id(session: Session, sample_book_id: int):
    """Test getting notes by book ID."""
    # Create a second book
    book2 = Book(title="Another Book", author="Another Author")
    session.add(book2)
    session.commit()
    session.refresh(book2)

    # Add notes to both books
    note1 = Note(content="Book 1 Note 1", content_hash="b1n1", book_id=sample_book_id)
    note2 = Note(content="Book 1 Note 2", content_hash="b1n2", book_id=sample_book_id)
    note3 = Note(content="Book 2 Note 1", content_hash="b2n1", book_id=book2.id)
    session.add_all([note1, note2, note3])
    session.commit()

    repo = NoteRepository(session)

    # Get notes for first book
    book1_notes = repo.get_by_book_id(sample_book_id)
    assert len(book1_notes) == 2
    contents = [note.content for note in book1_notes]
    assert "Book 1 Note 1" in contents
    assert "Book 1 Note 2" in contents

    # Get notes for second book
    book2_notes = repo.get_by_book_id(book2.id)
    assert len(book2_notes) == 1
    assert book2_notes[0].content == "Book 2 Note 1"


def test_get_by_book_id_empty(session: Session):
    """Test getting notes by book ID when no notes exist."""
    repo = NoteRepository(session)
    notes = repo.get_by_book_id(999)
    assert notes == []


def test_delete_existing_note(session: Session, sample_notes: list[NoteRead]):
    """Test deleting an existing note."""
    repo = NoteRepository(session)
    note_id = sample_notes[0].id

    # Verify note exists
    assert repo.get_by_id(note_id) is not None

    # Delete note
    repo.delete(note_id)

    # Verify note no longer exists
    assert repo.get_by_id(note_id) is None

    # Verify other notes still exist
    remaining_notes = repo.list_notes()
    assert len(remaining_notes) == 2


def test_delete_nonexistent_note(session: Session):
    """Test deleting a note that doesn't exist (should not raise error)."""
    repo = NoteRepository(session)
    # Should not raise an error
    repo.delete(999)


def test_get_random(session: Session, sample_notes: list[NoteRead]):
    """Test getting a random note."""
    repo = NoteRepository(session)
    random_note = repo.get_random()

    assert random_note is not None
    assert random_note.id in [note.id for note in sample_notes]


def test_get_random_empty(session: Session):
    """Test getting a random note when database is empty."""
    repo = NoteRepository(session)
    random_note = repo.get_random()
    assert random_note is None


@pytest.mark.skip(
    reason="SQLite doesn't support pgvector operations; requires PostgreSQL"
)
def test_find_similar_notes(session: Session, sample_book_id: int):
    """Test finding similar notes using embeddings."""
    # Create notes with embeddings
    embedding1 = [0.1] * 1536
    embedding2 = [0.2] * 1536  # Similar
    embedding3 = [0.9] * 1536  # Different

    note1 = Note(
        content="Note 1",
        content_hash="hash_sim_1",
        book_id=sample_book_id,
        embedding=embedding1,
    )
    note2 = Note(
        content="Note 2",
        content_hash="hash_sim_2",
        book_id=sample_book_id,
        embedding=embedding2,
    )
    note3 = Note(
        content="Note 3",
        content_hash="hash_sim_3",
        book_id=sample_book_id,
        embedding=embedding3,
    )
    session.add_all([note1, note2, note3])
    session.commit()
    session.refresh(note1)
    session.refresh(note2)
    session.refresh(note3)

    repo = NoteRepository(session)
    note1_read = NoteRead.model_validate(note1)

    # Find similar notes (should find note2, not note3)
    similar = repo.find_similar_notes(note1_read, limit=5, similarity_threshold=0.5)

    assert len(similar) >= 1
    # Note 1 should not be in results (excludes itself)
    assert all(note.id != note1.id for note in similar)


@pytest.mark.skip(
    reason="SQLite doesn't support pgvector operations; requires PostgreSQL"
)
def test_find_similar_notes_same_book_only(session: Session, sample_book_id: int):
    """Test that find_similar_notes only returns notes from the same book."""
    # Create a second book
    book2 = Book(title="Another Book", author="Another Author")
    session.add(book2)
    session.commit()
    session.refresh(book2)

    embedding = [0.1] * 1536

    # Add notes to both books with same embedding
    note1 = Note(
        content="Book 1 Note",
        content_hash="b1_hash",
        book_id=sample_book_id,
        embedding=embedding,
    )
    note2 = Note(
        content="Book 2 Note",
        content_hash="b2_hash",
        book_id=book2.id,
        embedding=embedding,
    )
    session.add_all([note1, note2])
    session.commit()
    session.refresh(note1)

    repo = NoteRepository(session)
    note1_read = NoteRead.model_validate(note1)

    # Find similar notes for note1
    similar = repo.find_similar_notes(note1_read, limit=5, similarity_threshold=0.5)

    # Should not include note from different book
    assert all(note.book_id == sample_book_id for note in similar)
    assert all(note.id != note2.id for note in similar)


def test_find_similar_notes_no_embedding(session: Session, sample_book_id: int):
    """Test find_similar_notes when the note has no embedding."""
    note = Note(
        content="No embedding",
        content_hash="no_embed",
        book_id=sample_book_id,
        embedding=None,
    )
    session.add(note)
    session.commit()
    session.refresh(note)

    repo = NoteRepository(session)
    note_read = NoteRead.model_validate(note)

    similar = repo.find_similar_notes(note_read, limit=5)
    assert similar == []


@pytest.mark.skip(
    reason="SQLite doesn't support pgvector operations; requires PostgreSQL"
)
def test_search_notes_by_embedding(session: Session, sample_book_id: int):
    """Test searching notes by embedding across all books."""
    # Create a second book
    book2 = Book(title="Another Book", author="Another Author")
    session.add(book2)
    session.commit()
    session.refresh(book2)

    search_embedding = [0.1] * 1536
    similar_embedding = [0.15] * 1536
    different_embedding = [0.9] * 1536

    # Add notes to different books
    note1 = Note(
        content="Book 1 Note",
        content_hash="search_b1",
        book_id=sample_book_id,
        embedding=similar_embedding,
    )
    note2 = Note(
        content="Book 2 Note",
        content_hash="search_b2",
        book_id=book2.id,
        embedding=similar_embedding,
    )
    note3 = Note(
        content="Different Note",
        content_hash="search_diff",
        book_id=sample_book_id,
        embedding=different_embedding,
    )
    session.add_all([note1, note2, note3])
    session.commit()

    repo = NoteRepository(session)

    # Search across all books
    results = repo.search_notes_by_embedding(
        search_embedding, limit=10, similarity_threshold=0.5
    )

    assert len(results) >= 2
    # Should include notes from both books (note1 and note2)
    book_ids = [note.book_id for note in results]
    assert sample_book_id in book_ids or book2.id in book_ids


@pytest.mark.skip(
    reason="SQLite doesn't support pgvector operations; requires PostgreSQL"
)
def test_search_notes_by_embedding_limit(session: Session, sample_book_id: int):
    """Test that search respects the limit parameter."""
    embedding = [0.1] * 1536

    # Add 5 notes with similar embeddings
    for i in range(5):
        note = Note(
            content=f"Note {i}",
            content_hash=f"search_limit_{i}",
            book_id=sample_book_id,
            embedding=embedding,
        )
        session.add(note)
    session.commit()

    repo = NoteRepository(session)

    # Search with limit of 3
    results = repo.search_notes_by_embedding(
        embedding, limit=3, similarity_threshold=0.5
    )

    assert len(results) <= 3


def test_get_note_counts_by_book_ids(session: Session, sample_book_id: int):
    """Test getting note counts for multiple books."""
    # Create a second book
    book2 = Book(title="Book 2", author="Author 2")
    book3 = Book(title="Book 3", author="Author 3")
    session.add_all([book2, book3])
    session.commit()
    session.refresh(book2)
    session.refresh(book3)

    # Add notes to books
    note1 = Note(content="B1 N1", content_hash="b1n1_count", book_id=sample_book_id)
    note2 = Note(content="B1 N2", content_hash="b1n2_count", book_id=sample_book_id)
    note3 = Note(content="B1 N3", content_hash="b1n3_count", book_id=sample_book_id)
    note4 = Note(content="B2 N1", content_hash="b2n1_count", book_id=book2.id)
    note5 = Note(content="B2 N2", content_hash="b2n2_count", book_id=book2.id)
    # Book 3 has no notes
    session.add_all([note1, note2, note3, note4, note5])
    session.commit()

    repo = NoteRepository(session)

    # Get counts for all books
    counts = repo.get_note_counts_by_book_ids([sample_book_id, book2.id, book3.id])

    assert counts[sample_book_id] == 3
    assert counts[book2.id] == 2
    # Book 3 should not appear in results (no notes)
    assert book3.id not in counts


def test_get_note_counts_by_book_ids_empty_list(session: Session):
    """Test getting note counts with empty book ID list."""
    repo = NoteRepository(session)
    counts = repo.get_note_counts_by_book_ids([])
    assert counts == {}


def test_get_note_counts_by_book_ids_nonexistent_books(session: Session):
    """Test getting note counts for books that don't exist."""
    repo = NoteRepository(session)
    counts = repo.get_note_counts_by_book_ids([999, 1000])
    assert counts == {}
