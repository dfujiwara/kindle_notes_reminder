"""
Test utilities and stub implementations for testing.

This module provides reusable stub implementations of repositories and clients
that can be used across different test files.
"""

from src.repositories.models import BookCreate, BookRead, Note, Evaluation
from src.repositories.interfaces import (
    BookRepositoryInterface,
    EvaluationRepositoryInterface,
    NoteRepositoryInterface,
)
from src.embedding_interface import EmbeddingClientInterface, EmbeddingError
from src.llm_interface import LLMClientInterface, LLMError
from src.types import Embedding
from datetime import datetime, timezone


class StubBookRepository(BookRepositoryInterface):
    """Stub implementation of BookRepository for testing."""

    def __init__(self, include_sample_book: bool = False):
        self.books: list[BookRead] = []
        if include_sample_book:
            sample_book = BookRead(
                id=1,
                title="The Pragmatic Programmer",
                author="David Thomas",
                created_at=datetime.now(timezone.utc),
            )
            self.books.append(sample_book)

    def add(self, book: BookCreate) -> BookRead:
        book_read = BookRead(
            id=len(self.books) + 1,
            title=book.title,
            author=book.author,
            created_at=datetime.now(timezone.utc),
        )
        self.books.append(book_read)
        return book_read

    def get(self, book_id: int) -> BookRead | None:
        return next((book for book in self.books if book.id == book_id), None)

    def list_books(self) -> list[BookRead]:
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

    def search_notes_by_embedding(
        self, embedding: Embedding, limit: int = 10, similarity_threshold: float = 0.5
    ) -> list[Note]:
        """
        Stub implementation of search_notes_by_embedding.
        Returns first `limit` notes from all books.
        """
        return self.notes[:limit]

    def get_note_counts_by_book_ids(self, book_ids: list[int]) -> dict[int, int]:
        result: dict[int, int] = {}
        book_ids_set = set(book_ids)
        for note in self.notes:
            if note.book_id in book_ids_set:
                result[note.book_id] = result.get(note.book_id, 0) + 1
        return result


class StubEvaluationRepository(EvaluationRepositoryInterface):
    def __init__(self):
        self.evaluations: list[Evaluation] = []

    def add(self, evaluation: Evaluation) -> Evaluation:
        evaluation.id = len(self.evaluations) + 1  # Simulate auto-increment ID
        self.evaluations.append(evaluation)
        return evaluation

    def get_by_note_id(self, note_id: int) -> list[Evaluation]:
        return [eval for eval in self.evaluations if eval.note_id == note_id]


class StubEmbeddingClient(EmbeddingClientInterface):
    """Stub implementation of EmbeddingClient for testing."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    async def generate_embedding(self, content: str) -> list[float]:
        if self.should_fail:
            raise EmbeddingError("Simulated embedding generation failure")
        # Return a simple mock embedding
        return [0.1] * 1536  # OpenAI embeddings are 1536 dimensions


class StubLLMClient(LLMClientInterface):
    """Stub implementation of LLMClient for testing."""

    def __init__(
        self, responses: list[str] = ["Test response"], should_fail: bool = False
    ):
        self.responses = responses
        self.should_fail = should_fail
        self.call_count = 0

    async def get_response(self, prompt: str, instruction: str) -> str:
        response = self.responses[self.call_count]
        self.call_count += 1
        if self.should_fail:
            raise LLMError("Simulated LLM generation failure")
        return response
