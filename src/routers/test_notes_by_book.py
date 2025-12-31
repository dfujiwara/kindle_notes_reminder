from fastapi.testclient import TestClient
from ..main import app
from ..repositories.models import NoteCreate, BookCreate
from ..config import settings
from .conftest import BookNoteDepsSetup

client = TestClient(app)


def test_get_notes_by_book_with_notes(setup_book_note_deps: BookNoteDepsSetup):
    _, note_repo = setup_book_note_deps(include_sample_book=True)

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


def test_get_notes_by_book_empty_book(setup_book_note_deps: BookNoteDepsSetup):
    _, _ = setup_book_note_deps(include_sample_book=True)

    # Make the request
    response = client.get("/books/1/notes")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    assert "notes" in data
    assert len(data["notes"]) == 0
    assert data["notes"] == []


def test_get_notes_by_book_nonexistent_book(setup_book_note_deps: BookNoteDepsSetup):
    _, note_repo = setup_book_note_deps(include_sample_book=False)

    # Add note for book_id=1, but we'll request book_id=999
    note = NoteCreate(
        content="Note for book 1",
        content_hash="hash1",
        book_id=1,
    )
    note_repo.add(note)

    # Make the request for non-existent book
    response = client.get("/books/999/notes")

    # Assertions
    assert response.status_code == 404


def test_get_notes_by_book_multiple_books(setup_book_note_deps: BookNoteDepsSetup):
    book_repo, note_repo = setup_book_note_deps(include_sample_book=True)

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


def test_get_notes_by_book_invalid_book_id():
    # Test with non-integer book_id
    response = client.get("/books/invalid/notes")
    assert response.status_code == 422  # Validation error


def test_get_notes_by_book_response_structure(setup_book_note_deps: BookNoteDepsSetup):
    _, note_repo = setup_book_note_deps(include_sample_book=True)

    # Add note with embedding to test that it's not exposed
    note = NoteCreate(
        content="Test note",
        content_hash="hash1",
        book_id=1,
        embedding=[0.1] * settings.embedding_dimension,
    )
    note_repo.add(note)

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
