from fastapi.testclient import TestClient
from .main import app, get_book_repository, get_note_repository
from .repositories.models import Book, Note
from .test_utils import StubBookRepository, StubNoteRepository

client = TestClient(app)


def test_get_books_empty():
    book_repo = StubBookRepository()

    app.dependency_overrides[get_book_repository] = lambda: book_repo

    try:
        response = client.get("/books")

        assert response.status_code == 200
        data = response.json()
        assert data["books"] == []
    finally:
        app.dependency_overrides.clear()


def test_get_books_with_books():
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()

    # Add books to the repository
    book1 = Book(title="Book 1", author="Author 1")
    book2 = Book(title="Book 2", author="Author 2")
    book_repo.add(book1)
    book_repo.add(book2)

    app.dependency_overrides[get_book_repository] = lambda: book_repo
    app.dependency_overrides[get_note_repository] = lambda: note_repo

    try:
        response = client.get("/books")

        assert response.status_code == 200
        data = response.json()
        assert len(data["books"]) == 2

        # Check first book
        assert data["books"][0]["id"] == 1
        assert data["books"][0]["title"] == "Book 1"
        assert data["books"][0]["author"] == "Author 1"
        assert data["books"][0]["note_count"] == 0

        # Check second book
        assert data["books"][1]["id"] == 2
        assert data["books"][1]["title"] == "Book 2"
        assert data["books"][1]["author"] == "Author 2"
        assert data["books"][1]["note_count"] == 0
    finally:
        app.dependency_overrides.clear()


def test_get_books_multiple_books_different_note_counts():
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()

    # Book with no notes
    book1 = Book(title="Book No Notes", author="Author 1")
    book_repo.add(book1)

    # Book with one note
    book2 = Book(title="Book One Note", author="Author 2")
    book_repo.add(book2)
    note2 = Note(content="Note", content_hash="hash2", book_id=2)
    note_repo.add(note2)

    # Book with multiple notes
    book3 = Book(title="Book Many Notes", author="Author 3")
    book_repo.add(book3)
    note3_1 = Note(content="Note 1", content_hash="hash3_1", book_id=3)
    note3_2 = Note(content="Note 2", content_hash="hash3_2", book_id=3)
    note3_3 = Note(content="Note 3", content_hash="hash3_3", book_id=3)
    note_repo.add(note3_1)
    note_repo.add(note3_2)
    note_repo.add(note3_3)

    app.dependency_overrides[get_book_repository] = lambda: book_repo
    app.dependency_overrides[get_note_repository] = lambda: note_repo

    try:
        response = client.get("/books")

        assert response.status_code == 200
        data = response.json()

        assert len(data["books"]) == 3

        # Check note counts
        assert data["books"][0]["note_count"] == 0
        assert data["books"][1]["note_count"] == 1
        assert data["books"][2]["note_count"] == 3

        # Check titles to verify order
        assert data["books"][0]["title"] == "Book No Notes"
        assert data["books"][1]["title"] == "Book One Note"
        assert data["books"][2]["title"] == "Book Many Notes"
    finally:
        app.dependency_overrides.clear()
