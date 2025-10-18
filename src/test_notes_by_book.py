from fastapi.testclient import TestClient
from .main import app
from .dependencies import get_note_repository, get_book_repository
from .repositories.models import NoteCreate, BookCreate
from .test_utils import StubNoteRepository, StubBookRepository

client = TestClient(app)


def test_get_notes_by_book_with_notes():
    # Setup stub repository with test data
    book_repo = StubBookRepository(include_sample_book=True)
    note_repo = StubNoteRepository()

    # Add notes to the repository
    note1 = NoteCreate(
        content="Note 1",
        content_hash="hash1",
        book_id=1,
    )
    note2 = NoteCreate(
        content="Note 2",
        content_hash="hash2",
        book_id=1,
    )
    note_repo.add(note1)
    note_repo.add(note2)

    # Override the dependency
    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_book_repository] = lambda: book_repo

    try:
        # Make the request
        response = client.get("/books/1/notes")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert "book" in data
        assert data["book"]["id"] == 1
        assert data["book"]["title"] == "The Pragmatic Programmer"
        assert data["book"]["author"] == "David Thomas"

        assert "notes" in data
        assert len(data["notes"]) == 2

        # Check first note
        assert data["notes"][0]["id"] == 1
        assert data["notes"][0]["content"] == "Note 1"
        assert "created_at" in data["notes"][0]

        # Check second note
        assert data["notes"][1]["id"] == 2
        assert data["notes"][1]["content"] == "Note 2"
        assert "created_at" in data["notes"][1]
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()


def test_get_notes_by_book_empty_book():
    # Setup empty stub repository
    book_repo = StubBookRepository(include_sample_book=True)
    note_repo = StubNoteRepository()

    # Override the dependency
    app.dependency_overrides[get_book_repository] = lambda: book_repo
    app.dependency_overrides[get_note_repository] = lambda: note_repo

    try:
        # Make the request
        response = client.get("/books/1/notes")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert "notes" in data
        assert len(data["notes"]) == 0
        assert data["notes"] == []
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()


def test_get_notes_by_book_nonexistent_book():
    # Setup stub repository with notes for different book
    book_repo = StubBookRepository(include_sample_book=False)
    note_repo = StubNoteRepository()

    # Add note for book_id=1, but we'll request book_id=999
    note = NoteCreate(
        content="Note for book 1",
        content_hash="hash1",
        book_id=1,
    )
    note_repo.add(note)

    # Override the dependency
    app.dependency_overrides[get_book_repository] = lambda: book_repo
    app.dependency_overrides[get_note_repository] = lambda: note_repo

    try:
        # Make the request for non-existent book
        response = client.get("/books/999/notes")

        # Assertions
        assert response.status_code == 404
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()


def test_get_notes_by_book_multiple_books():
    # Setup stub repository with notes for multiple books
    book_repo = StubBookRepository(include_sample_book=True)
    note_repo = StubNoteRepository()

    # Add additional book
    book_2 = BookCreate(author="Robert C. Martin", title="Clean Code")
    book_repo.add(book_2)
    # Add notes for book 1
    note1_1 = NoteCreate(
        content="Book 1 Note 1",
        content_hash="hash1",
        book_id=1,
    )
    note1_2 = NoteCreate(
        content="Book 1 Note 2",
        content_hash="hash2",
        book_id=1,
    )
    note_repo.add(note1_1)
    note_repo.add(note1_2)

    # Add note for book 2
    note2_1 = NoteCreate(
        content="Book 2 Note 1",
        content_hash="hash3",
        book_id=2,
    )
    note_repo.add(note2_1)

    # Override the dependency
    app.dependency_overrides[get_book_repository] = lambda: book_repo
    app.dependency_overrides[get_note_repository] = lambda: note_repo

    try:
        # Test book 1
        response1 = client.get("/books/1/notes")
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1["notes"]) == 2
        assert data1["notes"][0]["content"] == "Book 1 Note 1"
        assert data1["notes"][1]["content"] == "Book 1 Note 2"

        # Test book 2
        response2 = client.get("/books/2/notes")
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["notes"]) == 1
        assert data2["notes"][0]["content"] == "Book 2 Note 1"
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()


def test_get_notes_by_book_invalid_book_id():
    # Test with non-integer book_id
    response = client.get("/books/invalid/notes")
    assert response.status_code == 422  # Validation error


def test_get_notes_by_book_response_structure():
    # Setup stub repository with test data including embedding
    book_repo = StubBookRepository(include_sample_book=True)
    note_repo = StubNoteRepository()

    # Add note with embedding to test that it's not exposed
    note = NoteCreate(
        content="Test note",
        content_hash="hash1",
        book_id=1,
        embedding=[0.1] * 1536,  # Should not be included in response
    )
    note_repo.add(note)

    # Override the dependency
    app.dependency_overrides[get_book_repository] = lambda: book_repo
    app.dependency_overrides[get_note_repository] = lambda: note_repo

    try:
        # Make the request
        response = client.get("/books/1/notes")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "notes" in data
        assert len(data["notes"]) == 1

        note_data = data["notes"][0]
        # Check that only expected fields are present
        expected_fields = {"id", "content", "created_at"}
        assert set(note_data.keys()) == expected_fields

        # Check that sensitive fields are not exposed
        assert "embedding" not in note_data
        assert "content_hash" not in note_data
        assert "book_id" not in note_data
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()
