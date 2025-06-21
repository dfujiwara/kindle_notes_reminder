"""
Test utilities and stub implementations for testing.

This module provides reusable stub implementations of repositories and clients
that can be used across different test files.
"""

from src.repositories.models import Book, Note
from src.repositories.interfaces import BookRepositoryInterface, NoteRepositoryInterface
from src.embedding_interface import EmbeddingClientInterface, EmbeddingError
from src.types import Embedding


class StubBookRepository(BookRepositoryInterface):
    """Stub implementation of BookRepository for testing."""

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
    """Stub implementation of NoteRepository for testing."""

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

    def get_by_book_id(self, book_id: int) -> list[Note]:
        return [note for note in self.notes if note.book_id == book_id]

    def delete(self, note_id: int) -> None:
        self.notes = [note for note in self.notes if note.id != note_id]

    def get_random(self) -> Note | None:
        return self.notes[0] if self.notes else None

    def update_embedding(self, note: Note, embedding: Embedding) -> Note:
        note.embedding = embedding
        return note

    def find_similar_notes(
        self, note: Note, limit: int = 5, similarity_threshold: float = 0.3
    ) -> list[Note]:
        """
        Stub implementation of find_similar_notes.
        Returns first `limit` notes from the same book (excluding the input note).
        """
        return [n for n in self.notes if n.id != note.id and n.book_id == note.book_id][
            :limit
        ]


class StubEmbeddingClient(EmbeddingClientInterface):
    """Stub implementation of EmbeddingClient for testing."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    async def generate_embedding(self, content: str) -> list[float]:
        if self.should_fail:
            raise EmbeddingError("Simulated embedding generation failure")
        # Return a simple mock embedding
        return [0.1] * 1536  # OpenAI embeddings are 1536 dimensions
