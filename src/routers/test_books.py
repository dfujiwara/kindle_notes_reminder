from fastapi.testclient import TestClient
from ..main import app
from ..repositories.models import BookCreate, NoteCreate, Evaluation
from .conftest import BookNoteDepsSetup, BookDeleteDepsSetup

client = TestClient(app)


def test_get_books_empty(setup_book_note_deps: BookNoteDepsSetup):
    _, _ = setup_book_note_deps()

    response = client.get("/books")

    assert response.status_code == 200
    data = response.json()
    assert data["books"] == []


def test_get_books_with_books(setup_book_note_deps: BookNoteDepsSetup):
    book_repo, _ = setup_book_note_deps()

    # Add books to the repository
    book1 = BookCreate(title="Book 1", author="Author 1")
    book2 = BookCreate(title="Book 2", author="Author 2")
    book_repo.add(book1)
    book_repo.add(book2)

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


def test_get_books_multiple_books_different_note_counts(
    setup_book_note_deps: BookNoteDepsSetup,
):
    book_repo, note_repo = setup_book_note_deps()

    # Book with no notes
    book1 = BookCreate(title="Book No Notes", author="Author 1")
    book_repo.add(book1)

    # Book with one note
    book2 = BookCreate(title="Book One Note", author="Author 2")
    book_repo.add(book2)
    note2 = NoteCreate(content="Note", content_hash="hash2", book_id=2)
    note_repo.add(note2)

    # Book with multiple notes
    book3 = BookCreate(title="Book Many Notes", author="Author 3")
    book_repo.add(book3)
    note3_1 = NoteCreate(content="Note 1", content_hash="hash3_1", book_id=3)
    note3_2 = NoteCreate(content="Note 2", content_hash="hash3_2", book_id=3)
    note3_3 = NoteCreate(content="Note 3", content_hash="hash3_3", book_id=3)
    note_repo.add(note3_1)
    note_repo.add(note3_2)
    note_repo.add(note3_3)

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


def test_delete_book_not_found(setup_book_delete_deps: BookDeleteDepsSetup):
    setup_book_delete_deps()

    response = client.delete("/books/999")

    assert response.status_code == 404


def test_delete_book_with_notes_and_evaluations(
    setup_book_delete_deps: BookDeleteDepsSetup,
):
    book_repo, note_repo, eval_repo = setup_book_delete_deps()

    book = book_repo.add(BookCreate(title="Test Book", author="Author"))
    note = note_repo.add(
        NoteCreate(content="Note 1", content_hash="h1", book_id=book.id)
    )
    eval_repo.add(
        Evaluation(
            note_id=note.id,
            score=0.8,
            prompt="test prompt",
            response="test response",
            analysis="test analysis",
        )
    )

    response = client.delete(f"/books/{book.id}")

    assert response.status_code == 204
    assert book_repo.get(book.id) is None
    assert note_repo.get_by_book_id(book.id) == []
    assert eval_repo.evaluations == []
