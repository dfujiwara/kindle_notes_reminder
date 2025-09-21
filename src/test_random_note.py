import pytest
from typing import Callable, Generator
from fastapi.testclient import TestClient
from .main import (
    app,
    get_book_repository,
    get_note_repository,
    get_llm_client,
    get_evaluation_repository,
)
from .repositories.models import NoteCreate, BookCreate
from .test_utils import (
    StubNoteRepository,
    StubBookRepository,
    StubEvaluationRepository,
    StubLLMClient,
)

client = TestClient(app)

# Type alias for the setup function returned by fixture
SetupFunction = Callable[
    [list[str] | None],
    tuple[
        StubNoteRepository, StubBookRepository, StubEvaluationRepository, StubLLMClient
    ],
]


evaluation_response = (
    "Score: 0.85\nEvaluation: Well-structured and informative response."
)


@pytest.fixture
def setup_dependencies() -> Generator[SetupFunction, None, None]:
    """Fixture to set up dependency overrides with proper cleanup"""

    def _setup(
        llm_responses: list[str] | None = None,
    ) -> tuple[
        StubNoteRepository, StubBookRepository, StubEvaluationRepository, StubLLMClient
    ]:
        if llm_responses is None:
            llm_responses = ["Default additional context", evaluation_response]

        # Create fresh instances for each test call
        book_repo = StubBookRepository()
        note_repo = StubNoteRepository()
        evaluation_repo = StubEvaluationRepository()
        llm_client = StubLLMClient(responses=llm_responses)

        # Override dependencies
        app.dependency_overrides[get_book_repository] = lambda: book_repo
        app.dependency_overrides[get_note_repository] = lambda: note_repo
        app.dependency_overrides[get_llm_client] = lambda: llm_client
        app.dependency_overrides[get_evaluation_repository] = lambda: evaluation_repo

        return note_repo, book_repo, evaluation_repo, llm_client

    yield _setup

    # Cleanup
    app.dependency_overrides.clear()


def test_get_random_note_success(setup_dependencies: SetupFunction):
    # Setup with custom LLM responses
    note_repo, book_repo, _, _ = setup_dependencies(
        ["This is additional context about the note", evaluation_response]
    )

    # Create a book
    book = BookCreate(title="Test Book", author="Test Author")
    book = book_repo.add(book)

    # Add notes to the repository
    note1 = NoteCreate(
        content="Primary note content",
        content_hash="hash1",
        book_id=book.id,
    )
    note2 = NoteCreate(
        content="Related note content",
        content_hash="hash2",
        book_id=book.id,
    )
    note_repo.add(note1)
    note_repo.add(note2)

    # Make the request
    response = client.get("/random")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "book" in data
    assert "note" in data
    assert "additional_context" in data
    assert "related_notes" in data

    # Check content
    assert data["book"] == {
        "id": book.id,
        "title": "Test Book",
        "author": "Test Author",
        "created_at": book.created_at.isoformat().replace("+00:00", "Z"),
    }
    assert data["note"] == "Primary note content"
    assert data["additional_context"] == "This is additional context about the note"

    # Check related notes (should be note2 since note1 is the primary)
    assert len(data["related_notes"]) == 1
    assert data["related_notes"][0]["id"] == 2
    assert data["related_notes"][0]["content"] == "Related note content"


def test_get_random_note_no_notes(setup_dependencies: SetupFunction):
    # Setup empty stub repository
    _, _, _, _ = setup_dependencies(["additional context", evaluation_response])

    # Make the request
    response = client.get("/random")

    # Assertions
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "No notes found"


def test_get_random_note_single_note(setup_dependencies: SetupFunction):
    # Setup stub repository with single note
    note_repo, book_repo, _, _ = setup_dependencies(
        ["Context for single note", evaluation_response]
    )

    # Create a book
    book = BookCreate(title="Solo Book", author="Solo Author")
    book = book_repo.add(book)

    # Add single note
    note = NoteCreate(
        content="Only note content",
        content_hash="hash1",
        book_id=book.id,
    )
    note_repo.add(note)

    # Make the request
    response = client.get("/random")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    assert data["book"] == {
        "id": book.id,
        "title": "Solo Book",
        "author": "Solo Author",
        "created_at": book.created_at.isoformat().replace("+00:00", "Z"),
    }
    assert data["note"] == "Only note content"
    assert data["additional_context"] == "Context for single note"

    # Should have no related notes since there's only one note
    assert len(data["related_notes"]) == 0


def test_get_random_note_multiple_books(setup_dependencies: SetupFunction):
    # Setup stub repository with notes from multiple books
    note_repo, book_repo, _, _ = setup_dependencies(
        ["Cross-book context", evaluation_response]
    )

    # Create books
    book1 = BookCreate(title="Book One", author="Author One")
    book2 = BookCreate(title="Book Two", author="Author Two")
    book1 = book_repo.add(book1)
    book2 = book_repo.add(book2)

    # Add notes from different books
    note1 = NoteCreate(
        content="Note from book 1",
        content_hash="hash1",
        book_id=book1.id,
    )
    note2 = NoteCreate(
        content="Another note from book 1",
        content_hash="hash2",
        book_id=book1.id,
    )
    note3 = NoteCreate(
        content="Note from book 2",
        content_hash="hash3",
        book_id=book2.id,
    )

    note_repo.add(note1)
    note_repo.add(note2)
    note_repo.add(note3)

    # Make the request (will return first note since StubNoteRepository.get_random() returns first note)
    response = client.get("/random")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    assert data["book"] == {
        "id": book1.id,
        "title": "Book One",
        "author": "Author One",
        "created_at": book1.created_at.isoformat().replace("+00:00", "Z"),
    }
    assert data["note"] == "Note from book 1"
    assert data["additional_context"] == "Cross-book context"

    # Should only include related notes from the same book
    assert len(data["related_notes"]) == 1
    assert data["related_notes"][0]["content"] == "Another note from book 1"


def test_get_random_note_response_structure(setup_dependencies: SetupFunction):
    # Test that response doesn't expose sensitive fields
    note_repo, book_repo, _, _ = setup_dependencies(
        ["Structure test", evaluation_response]
    )

    # Create book and note with all fields
    book = BookCreate(title="Structure Book", author="Structure Author")
    book = book_repo.add(book)

    note = NoteCreate(
        content="Structure note",
        content_hash="secret_hash",
        book_id=book.id,
        embedding=[0.1] * 1536,  # Should not be exposed
    )
    note_repo.add(note)

    # Make the request
    response = client.get("/random")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check that only expected fields are present at top level
    expected_fields = {
        "book",
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
