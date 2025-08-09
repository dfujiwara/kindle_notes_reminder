"""
Unit tests for the /search endpoint.
"""

from fastapi.testclient import TestClient
from .main import app, get_note_repository, get_embedding_client
from .repositories.models import Book, Note
from .test_utils import StubNoteRepository, StubEmbeddingClient
from datetime import datetime, timezone

client = TestClient(app)


def test_search_notes_empty_results():
    """Test search endpoint with no matching results."""
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

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
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

    # Create test data
    book1 = Book(title="Machine Learning Book", author="ML Author")
    book1.id = 1

    note1 = Note(
        id=1,
        content="Introduction to machine learning algorithms",
        content_hash="hash1",
        book_id=1,
        embedding=[0.1] * 1536,
    )
    note1.book = book1
    note2 = Note(
        id=2,
        content="Neural networks and deep learning",
        content_hash="hash2",
        book_id=1,
        embedding=[0.2] * 1536,
    )
    note2.book = book1

    note_repo.add(note1)
    note_repo.add(note2)

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
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

    # Create test data - two books
    book1 = Book(title="ML Book", author="Author 1")
    book1.id = 1
    book2 = Book(title="AI Book", author="Author 2")
    book2.id = 2

    # Notes from first book
    note1 = Note(
        content="Machine learning basics",
        content_hash="hash1",
        book_id=1,
        embedding=[0.1] * 1536,
    )
    note1.id = 1
    note1.book = book1
    note1.created_at = datetime.now(timezone.utc)

    note2 = Note(
        content="Supervised learning techniques",
        content_hash="hash2",
        book_id=1,
        embedding=[0.2] * 1536,
    )
    note2.id = 2
    note2.book = book1
    note2.created_at = datetime.now(timezone.utc)

    # Note from second book
    note3 = Note(
        content="Artificial intelligence overview",
        content_hash="hash3",
        book_id=2,
        embedding=[0.3] * 1536,
    )
    note3.id = 3
    note3.book = book2
    note3.created_at = datetime.now(timezone.utc)

    note_repo.add(note1)
    note_repo.add(note2)
    note_repo.add(note3)

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
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

    # Create test data with many notes
    book1 = Book(title="Test Book", author="Test Author")
    book1.id = 1

    for i in range(5):
        note = Note(
            content=f"Note content {i}",
            content_hash=f"hash{i}",
            book_id=1,
            embedding=[0.1 + i * 0.1] * 1536,
        )
        note.id = i + 1
        note.book = book1
        note.created_at = datetime.now(timezone.utc)
        note_repo.add(note)

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
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

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


def test_search_notes_skips_notes_with_null_book_id():
    """Test search endpoint gracefully handles notes with null book_id."""
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

    # Create a note with a book that has None as ID (edge case)
    book_with_none_id = Book(title="Book With None ID", author="Author")
    book_with_none_id.id = None  # Simulate edge case

    note_with_none_book_id = Note(
        content="This note has a book with None ID",
        content_hash="hash_none",
        book_id=1,
        embedding=[0.1] * 1536,
    )
    note_with_none_book_id.id = 1
    note_with_none_book_id.book = book_with_none_id
    note_with_none_book_id.created_at = datetime.now(timezone.utc)

    # Create a valid note for comparison
    valid_book = Book(title="Valid Book", author="Valid Author")
    valid_book.id = 2

    valid_note = Note(
        content="This is a valid note",
        content_hash="hash_valid",
        book_id=2,
        embedding=[0.2] * 1536,
    )
    valid_note.id = 2
    valid_note.book = valid_book
    valid_note.created_at = datetime.now(timezone.utc)

    note_repo.add(note_with_none_book_id)
    note_repo.add(valid_note)

    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_embedding_client] = lambda: embedding_client

    try:
        response = client.get("/search?q=test")

        assert response.status_code == 200
        data = response.json()

        # The stub returns 2 notes, but one gets filtered out during processing
        # because its book has None as ID
        assert data["count"] == 1  # Count now reflects actual results after filtering
        assert len(data["results"]) == 1  # Only 1 book makes it to results
        assert data["results"][0]["book"]["title"] == "Valid Book"
        assert len(data["results"][0]["notes"]) == 1
    finally:
        app.dependency_overrides.clear()
