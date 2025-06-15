import pytest
from src.notebook_processor import process_notebook_result
from src.notebook_parser import NotebookParseResult
from src.repositories.models import Book, Note
from src.repositories.interfaces import BookRepositoryInterface, NoteRepositoryInterface
from src.embedding_interface import EmbeddingClientInterface, EmbeddingError
from src.types import Embedding
import hashlib


class StubBookRepository(BookRepositoryInterface):
    def __init__(self):
        self.books: list[Book] = []

    def add(self, book: Book) -> Book:
        book.id = len(self.books) + 1  # Simulate auto-increment ID
        self.books.append(book)
        return book

    def get(self, book_id: int) -> Book | None:
        return next((book for book in self.books if book.id == book_id), None)

    def list_books(self) -> list[Book]:
        return self.books

    def delete(self, book_id: int) -> None:
        self.books = [book for book in self.books if book.id != book_id]


class StubNoteRepository(NoteRepositoryInterface):
    def __init__(self):
        self.notes: list[Note] = []

    def add(self, note: Note) -> Note:
        note.id = len(self.notes) + 1  # Simulate auto-increment ID
        self.notes.append(note)
        return note

    def get(self, note_id: int) -> Note | None:
        return next((note for note in self.notes if note.id == note_id), None)

    def list_notes(self) -> list[Note]:
        return self.notes

    def delete(self, note_id: int) -> None:
        self.notes = [note for note in self.notes if note.id != note_id]

    def get_random(self) -> Note | None:
        return self.notes[0] if self.notes else None

    def update_embedding(self, note: Note, embedding: Embedding) -> Note:
        note.embedding = embedding
        return note


class StubEmbeddingClient(EmbeddingClientInterface):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    async def generate_embedding(self, content: str) -> list[float]:
        if self.should_fail:
            raise EmbeddingError("Simulated embedding generation failure")
        # Return a simple mock embedding
        return [0.1] * 1536  # OpenAI embeddings are 1536 dimensions


@pytest.mark.asyncio
async def test_process_notebook_result_success():
    # Setup
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

    # Create a sample NotebookParseResult
    result = NotebookParseResult(
        book_title="Sample Book",
        authors_str="Author Name",
        notes=["Note 1", "Note 2"],
        total_notes=2,
    )

    # Call the function
    processed_result = await process_notebook_result(
        result, book_repo, note_repo, embedding_client
    )

    # Assertions
    assert processed_result["book"]["title"] == "Sample Book"
    assert processed_result["book"]["author"] == "Author Name"
    assert len(processed_result["notes"]) == 2
    assert processed_result["notes"][0]["content"] == "Note 1"
    assert processed_result["notes"][1]["content"] == "Note 2"
    assert (
        "embedding" not in processed_result["notes"][0]
    )  # Embedding should be excluded


@pytest.mark.asyncio
async def test_process_notebook_result_return_value():
    # Setup
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

    # Create a sample NotebookParseResult
    result = NotebookParseResult(
        book_title="Sample Book",
        authors_str="Author Name",
        notes=["Note 1", "Note 2"],
        total_notes=2,
    )

    # Call the function and get the return value
    returned_value = await process_notebook_result(
        result, book_repo, note_repo, embedding_client
    )

    # Assertions for the book
    assert returned_value["book"] == {
        "id": 1,
        "title": "Sample Book",
        "author": "Author Name",
    }

    # Assertions for the notes
    expected_notes = [
        {
            "id": 1,
            "book_id": 1,
            "content": "Note 1",
            "content_hash": hashlib.sha256("Note 1".encode("utf-8")).hexdigest(),
        },
        {
            "id": 2,
            "book_id": 1,
            "content": "Note 2",
            "content_hash": hashlib.sha256("Note 2".encode("utf-8")).hexdigest(),
        },
    ]

    assert len(returned_value["notes"]) == len(expected_notes)
    for note, expected in zip(returned_value["notes"], expected_notes):
        assert note == expected


@pytest.mark.asyncio
async def test_process_notebook_result_embedding_failure():
    # Setup
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient(should_fail=True)

    # Create a sample NotebookParseResult
    result = NotebookParseResult(
        book_title="Sample Book",
        authors_str="Author Name",
        notes=["Note 1"],
        total_notes=1,
    )

    # Call the function and expect it to raise EmbeddingError
    with pytest.raises(EmbeddingError):
        await process_notebook_result(result, book_repo, note_repo, embedding_client)
