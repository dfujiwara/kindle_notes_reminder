from fastapi.testclient import TestClient
from datetime import datetime, timezone
from .main import app, get_note_repository, get_llm_client
from .repositories.models import Note, Book
from .test_utils import StubNoteRepository, StubLLMClient

client = TestClient(app)


def test_get_random_note_success():
    # Setup stub repository with test data
    note_repo = StubNoteRepository()
    llm_client = StubLLMClient(response="This is additional context about the note")
    created_at = datetime.now(timezone.utc)

    # Create a book
    book = Book(id=1, title="Test Book", author="Test Author")

    # Add notes to the repository
    note1 = Note(
        id=1,
        content="Primary note content",
        content_hash="hash1",
        book_id=1,
        created_at=created_at,
        book=book,
    )
    note2 = Note(
        id=2,
        content="Related note content",
        content_hash="hash2",
        book_id=1,
        created_at=created_at,
        book=book,
    )
    note_repo.add(note1)
    note_repo.add(note2)

    # Override dependencies
    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_llm_client] = lambda: llm_client

    try:
        # Make the request
        response = client.get("/random")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "book" in data
        assert "author" in data
        assert "note" in data
        assert "additional_context" in data
        assert "related_notes" in data

        # Check content
        assert data["book"] == "Test Book"
        assert data["author"] == "Test Author"
        assert data["note"] == "Primary note content"
        assert data["additional_context"] == "This is additional context about the note"

        # Check related notes (should be note2 since note1 is the primary)
        assert len(data["related_notes"]) == 1
        assert data["related_notes"][0]["id"] == 2
        assert data["related_notes"][0]["content"] == "Related note content"

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


def test_get_random_note_no_notes():
    # Setup empty stub repository
    note_repo = StubNoteRepository()
    llm_client = StubLLMClient()

    # Override dependencies
    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_llm_client] = lambda: llm_client

    try:
        # Make the request
        response = client.get("/random")

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "No notes found"

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


def test_get_random_note_single_note():
    # Setup stub repository with single note
    note_repo = StubNoteRepository()
    llm_client = StubLLMClient(response="Context for single note")
    created_at = datetime.now(timezone.utc)

    # Create a book
    book = Book(id=1, title="Solo Book", author="Solo Author")

    # Add single note
    note = Note(
        id=1,
        content="Only note content",
        content_hash="hash1",
        book_id=1,
        created_at=created_at,
        book=book,
    )
    note_repo.add(note)

    # Override dependencies
    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_llm_client] = lambda: llm_client

    try:
        # Make the request
        response = client.get("/random")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["book"] == "Solo Book"
        assert data["author"] == "Solo Author"
        assert data["note"] == "Only note content"
        assert data["additional_context"] == "Context for single note"

        # Should have no related notes since there's only one note
        assert len(data["related_notes"]) == 0

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


def test_get_random_note_multiple_books():
    # Setup stub repository with notes from multiple books
    note_repo = StubNoteRepository()
    llm_client = StubLLMClient(response="Cross-book context")
    created_at = datetime.now(timezone.utc)

    # Create books
    book1 = Book(id=1, title="Book One", author="Author One")
    book2 = Book(id=2, title="Book Two", author="Author Two")

    # Add notes from different books
    note1 = Note(
        id=1,
        content="Note from book 1",
        content_hash="hash1",
        book_id=1,
        created_at=created_at,
        book=book1,
    )
    note2 = Note(
        id=2,
        content="Another note from book 1",
        content_hash="hash2",
        book_id=1,
        created_at=created_at,
        book=book1,
    )
    note3 = Note(
        id=3,
        content="Note from book 2",
        content_hash="hash3",
        book_id=2,
        created_at=created_at,
        book=book2,
    )

    note_repo.add(note1)
    note_repo.add(note2)
    note_repo.add(note3)

    # Override dependencies
    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_llm_client] = lambda: llm_client

    try:
        # Make the request (will return first note since StubNoteRepository.get_random() returns first note)
        response = client.get("/random")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["book"] == "Book One"
        assert data["author"] == "Author One"
        assert data["note"] == "Note from book 1"
        assert data["additional_context"] == "Cross-book context"

        # Should only include related notes from the same book
        assert len(data["related_notes"]) == 1
        assert data["related_notes"][0]["content"] == "Another note from book 1"

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


def test_get_random_note_response_structure():
    # Test that response doesn't expose sensitive fields
    note_repo = StubNoteRepository()
    llm_client = StubLLMClient(response="Structure test")
    created_at = datetime.now(timezone.utc)

    # Create book and note with all fields
    book = Book(id=1, title="Structure Book", author="Structure Author")
    note = Note(
        id=1,
        content="Structure note",
        content_hash="secret_hash",
        book_id=1,
        created_at=created_at,
        book=book,
        embedding=[0.1] * 1536,  # Should not be exposed
    )
    note_repo.add(note)

    # Override dependencies
    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_llm_client] = lambda: llm_client

    try:
        # Make the request
        response = client.get("/random")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        # Check that only expected fields are present at top level
        expected_fields = {
            "book",
            "author",
            "note",
            "additional_context",
            "related_notes",
        }
        assert set(data.keys()) == expected_fields

        # Check that sensitive fields are not exposed anywhere
        response_str = response.text
        assert "content_hash" not in response_str
        assert "embedding" not in response_str
        assert "book_id" not in response_str

        # Related notes should only have id and content
        if data["related_notes"]:
            note_data = data["related_notes"][0]
            expected_note_fields = {"id", "content"}
            assert set(note_data.keys()) == expected_note_fields

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()
