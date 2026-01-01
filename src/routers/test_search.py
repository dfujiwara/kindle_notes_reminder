"""
Unit tests for the /search endpoint.
"""

from fastapi.testclient import TestClient
from ..main import app
from ..repositories.models import BookCreate, NoteCreate
from ..config import settings
from .conftest import SearchDepsSetup

client = TestClient(app)


def test_search_notes_empty_results(setup_search_deps: SearchDepsSetup):
    """Test search endpoint with no matching results."""
    _, _, _, _, _ = setup_search_deps()

    response = client.get("/search?q=nonexistent")

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "nonexistent"
    assert data["books"] == []
    assert data["urls"] == []
    assert data["count"] == 0


def test_search_notes_single_book(setup_search_deps: SearchDepsSetup):
    """Test search endpoint with results from a single book."""
    book_repo, note_repo, _, _, _ = setup_search_deps()

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

    response = client.get("/search?q=machine learning&limit=10")

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "machine learning"
    assert data["count"] == 2
    assert len(data["books"]) == 1  # One book
    assert len(data["urls"]) == 0  # No URLs

    # Check book structure
    book_result = data["books"][0]
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


def test_search_notes_multiple_books(setup_search_deps: SearchDepsSetup):
    """Test search endpoint with results grouped by multiple books."""
    book_repo, note_repo, _, _, _ = setup_search_deps()

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

    response = client.get("/search?q=learning")

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "learning"
    assert data["count"] == 3
    assert len(data["books"]) == 2  # Two books
    assert len(data["urls"]) == 0  # No URLs

    # Results should be grouped by book
    book_ids = {result["book"]["id"] for result in data["books"]}
    assert book_ids == {1, 2}

    # Find results for each book
    book1_result = next(r for r in data["books"] if r["book"]["id"] == 1)
    book2_result = next(r for r in data["books"] if r["book"]["id"] == 2)

    assert book1_result["book"]["title"] == "ML Book"
    assert len(book1_result["notes"]) == 2

    assert book2_result["book"]["title"] == "AI Book"
    assert len(book2_result["notes"]) == 1


def test_search_notes_with_limit(setup_search_deps: SearchDepsSetup):
    """Test search endpoint respects the limit parameter."""
    book_repo, note_repo, _, _, _ = setup_search_deps()

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

    response = client.get("/search?q=test&limit=3")

    assert response.status_code == 200
    data = response.json()
    # With limit=3, we allocate 1 to notes (limit//2=1) and 2 to chunks (limit-1=2)
    # Since we only have notes and no chunks, we get 1 note
    assert len(data["books"]) == 1  # One book
    assert len(data["books"][0]["notes"]) >= 1  # At least 1 note (due to allocation)
    assert len(data["urls"]) == 0  # No URLs


def test_search_notes_max_limit(setup_search_deps: SearchDepsSetup):
    """Test search endpoint enforces maximum limit of 50."""
    _, _, _, _, _ = setup_search_deps()

    response = client.get("/search?q=test&limit=100")

    assert response.status_code == 200
    # The endpoint should internally limit to 50, but since we have no data,
    # we just verify it doesn't crash and returns valid response
    data = response.json()
    assert data["query"] == "test"
    assert data["count"] == 0
    assert data["books"] == []
    assert data["urls"] == []


def test_search_mixed_notes_and_chunks(setup_search_deps: SearchDepsSetup):
    """Test search endpoint with results from both notes and URL chunks."""
    book_repo, note_repo, _, url_repo, chunk_repo = setup_search_deps()

    # Create test data - book with notes
    book1 = book_repo.add(BookCreate(title="Test Book", author="Test Author"))
    note1 = NoteCreate(
        content="Machine learning algorithms explained",
        content_hash="note_hash1",
        book_id=book1.id,
        embedding=[0.1] * settings.embedding_dimension,
    )
    note_repo.add(note1)

    # Create test data - URL with chunks
    from src.repositories.models import URLCreate, URLChunkCreate

    url1 = url_repo.add(URLCreate(url="https://example.com", title="Example Article"))
    chunk1 = URLChunkCreate(
        content="Deep learning is a subset of machine learning",
        content_hash="chunk_hash1",
        url_id=url1.id,
        chunk_order=1,
        is_summary=False,
        embedding=[0.15] * settings.embedding_dimension,
    )
    chunk_repo.add(chunk1)

    response = client.get("/search?q=machine learning")

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "machine learning"
    # Should have both notes and chunks
    assert len(data["books"]) >= 1  # At least 1 book
    assert len(data["urls"]) >= 1  # At least 1 URL
    # Total count should include both
    assert data["count"] >= 2
