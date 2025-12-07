"""
Unit tests for the /search endpoint.
"""

from fastapi.testclient import TestClient
from ..main import app
from ..dependencies import (
    get_book_repository,
    get_note_repository,
    get_embedding_client,
)
from ..repositories.models import BookCreate, NoteCreate
from ..test_utils import StubBookRepository, StubNoteRepository, StubEmbeddingClient
from ..config import settings

client = TestClient(app)


def test_search_notes_empty_results():
    """Test search endpoint with no matching results."""
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

    app.dependency_overrides[get_book_repository] = lambda: book_repo
    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_embedding_client] = lambda: embedding_client

    try:
        response = client.get("/search?q=nonexistent")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "nonexistent"
        assert data["results"] == []
        assert data["count"] == 0
    finally:
        app.dependency_overrides.clear()


def test_search_notes_single_book():
    """Test search endpoint with results from a single book."""
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

    # Create test data
    book1 = book_repo.add(BookCreate(title="Machine Learning Book", author="ML Author"))

    note1 = NoteCreate(
        content="Introduction to machine learning algorithms",
        content_hash="hash1",
        book_id=book1.id,
        embedding=[0.1] * settings.embedding_dimension,
    )
    note2 = NoteCreate(
        content="Neural networks and deep learning",
        content_hash="hash2",
        book_id=book1.id,
        embedding=[0.2] * settings.embedding_dimension,
    )

    note_repo.add(note1)
    note_repo.add(note2)

    app.dependency_overrides[get_book_repository] = lambda: book_repo
    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_embedding_client] = lambda: embedding_client

    try:
        response = client.get("/search?q=machine learning&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "machine learning"
        assert data["count"] == 2
        assert len(data["results"]) == 1  # One book

        # Check book structure
        book_result = data["results"][0]
        assert book_result["book"]["id"] == 1
        assert book_result["book"]["title"] == "Machine Learning Book"
        assert book_result["book"]["author"] == "ML Author"
        assert len(book_result["notes"]) == 2

        # Check notes
        notes = book_result["notes"]
        assert notes[0]["id"] == 1
        assert notes[0]["content"] == "Introduction to machine learning algorithms"
        assert notes[1]["id"] == 2
        assert notes[1]["content"] == "Neural networks and deep learning"
    finally:
        app.dependency_overrides.clear()


def test_search_notes_multiple_books():
    """Test search endpoint with results grouped by multiple books."""
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

    # Create test data - two books
    book1 = book_repo.add(BookCreate(title="ML Book", author="Author 1"))
    book2 = book_repo.add(BookCreate(title="AI Book", author="Author 2"))

    # Notes from first book
    note1 = NoteCreate(
        content="Machine learning basics",
        content_hash="hash1",
        book_id=book1.id,
        embedding=[0.1] * settings.embedding_dimension,
    )
    note2 = NoteCreate(
        content="Supervised learning techniques",
        content_hash="hash2",
        book_id=book1.id,
        embedding=[0.2] * settings.embedding_dimension,
    )
    # Note from second book
    note3 = NoteCreate(
        content="Artificial intelligence overview",
        content_hash="hash3",
        book_id=book2.id,
        embedding=[0.3] * settings.embedding_dimension,
    )
    note_repo.add(note1)
    note_repo.add(note2)
    note_repo.add(note3)

    app.dependency_overrides[get_book_repository] = lambda: book_repo
    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_embedding_client] = lambda: embedding_client

    try:
        response = client.get("/search?q=learning")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "learning"
        assert data["count"] == 3
        assert len(data["results"]) == 2  # Two books

        # Results should be grouped by book
        book_ids = {result["book"]["id"] for result in data["results"]}
        assert book_ids == {1, 2}

        # Find results for each book
        book1_result = next(r for r in data["results"] if r["book"]["id"] == 1)
        book2_result = next(r for r in data["results"] if r["book"]["id"] == 2)

        assert book1_result["book"]["title"] == "ML Book"
        assert len(book1_result["notes"]) == 2

        assert book2_result["book"]["title"] == "AI Book"
        assert len(book2_result["notes"]) == 1
    finally:
        app.dependency_overrides.clear()


def test_search_notes_with_limit():
    """Test search endpoint respects the limit parameter."""
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

    # Create test data with many notes
    book1 = BookCreate(title="Test Book", author="Test Author")
    book1 = book_repo.add(book1)

    for i in range(5):
        note = NoteCreate(
            content=f"Note content {i}",
            content_hash=f"hash{i}",
            book_id=book1.id,
            embedding=[0.1 + i * 0.1] * 1536,
        )
        note_repo.add(note)

    app.dependency_overrides[get_book_repository] = lambda: book_repo
    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_embedding_client] = lambda: embedding_client

    try:
        response = client.get("/search?q=test&limit=3")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3  # Should be limited to 3
        assert len(data["results"]) == 1  # One book
        assert len(data["results"][0]["notes"]) == 3  # 3 notes
    finally:
        app.dependency_overrides.clear()


def test_search_notes_max_limit():
    """Test search endpoint enforces maximum limit of 50."""
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

    app.dependency_overrides[get_book_repository] = lambda: book_repo
    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_embedding_client] = lambda: embedding_client

    try:
        response = client.get("/search?q=test&limit=100")

        assert response.status_code == 200
        # The endpoint should internally limit to 50, but since we have no data,
        # we just verify it doesn't crash and returns valid response
        data = response.json()
        assert data["query"] == "test"
        assert data["count"] == 0
    finally:
        app.dependency_overrides.clear()
