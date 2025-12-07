"""
Test utilities and stub implementations for testing.

This module provides reusable stub implementations of repositories and clients
that can be used across different test files.
"""

from src.repositories.models import (
    BookCreate,
    BookResponse,
    NoteCreate,
    NoteRead,
    Evaluation,
)
from src.repositories.interfaces import (
    BookRepositoryInterface,
    EvaluationRepositoryInterface,
    NoteRepositoryInterface,
)
from src.embedding_interface import EmbeddingClientInterface, EmbeddingError
from src.llm_interface import LLMClientInterface, LLMError
from src.types import Embedding
from src.config import settings
from datetime import datetime, timezone
from typing import AsyncGenerator


class StubBookRepository(BookRepositoryInterface):
    """Stub implementation of BookRepository for testing."""

    def __init__(self, include_sample_book: bool = False):
        self.books: list[BookResponse] = []
        if include_sample_book:
            sample_book = BookResponse(
                id=1,
                title="The Pragmatic Programmer",
                author="David Thomas",
                created_at=datetime.now(timezone.utc),
            )
            self.books.append(sample_book)

    def add(self, book: BookCreate) -> BookResponse:
        book_read = BookResponse(
            id=len(self.books) + 1,
            title=book.title,
            author=book.author,
            created_at=datetime.now(timezone.utc),
        )
        self.books.append(book_read)
        return book_read

    def get(self, book_id: int) -> BookResponse | None:
        return next((book for book in self.books if book.id == book_id), None)

    def list_books(self) -> list[BookResponse]:
        return self.books

    def get_by_ids(self, book_ids: list[int]) -> list[BookResponse]:
        return [b for b in self.books if b.id in book_ids]

    def delete(self, book_id: int) -> None:
        self.books = [book for book in self.books if book.id != book_id]


class StubNoteRepository(NoteRepositoryInterface):
    """Stub implementation of NoteRepository for testing."""

    def __init__(self):
        self.notes: list[NoteRead] = []

    def add(self, note: NoteCreate) -> NoteRead:
        note_read = NoteRead(
            id=len(self.notes) + 1,
            created_at=datetime.now(timezone.utc),
            book_id=note.book_id,
            content=note.content,
            content_hash=note.content_hash,
        )
        self.notes.append(note_read)
        return note_read

    def get(self, note_id: int, book_id: int) -> NoteRead | None:
        return next(
            (
                note
                for note in self.notes
                if note.id == note_id and note.book_id == book_id
            ),
            None,
        )

    def get_by_id(self, note_id: int) -> NoteRead | None:
        return next((note for note in self.notes if note.id == note_id), None)

    def list_notes(self) -> list[NoteRead]:
        return self.notes

    def get_by_book_id(self, book_id: int) -> list[NoteRead]:
        return [note for note in self.notes if note.book_id == book_id]

    def delete(self, note_id: int) -> None:
        self.notes = [note for note in self.notes if note.id != note_id]

    def get_random(self) -> NoteRead | None:
        return self.notes[0] if self.notes else None

    def find_similar_notes(
        self, note: NoteRead, limit: int = 5, similarity_threshold: float = 0.3
    ) -> list[NoteRead]:
        """
        Stub implementation of find_similar_notes.
        Returns first `limit` notes from the same book (excluding the input note).
        """
        return [n for n in self.notes if n.id != note.id and n.book_id == note.book_id][
            :limit
        ]

    def search_notes_by_embedding(
        self, embedding: Embedding, limit: int = 10, similarity_threshold: float = 0.5
    ) -> list[NoteRead]:
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
        # Return a simple mock embedding using configured dimension
        return [0.1] * settings.embedding_dimension


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

    async def get_response_stream(
        self, prompt: str, instruction: str
    ) -> AsyncGenerator[str, None]:
        """Stub streaming response that yields the response in chunks."""
        response = await self.get_response(prompt, instruction)
        # Yield response in chunks (simulate streaming)
        chunk_size = 10
        for i in range(0, len(response), chunk_size):
            yield response[i : i + chunk_size]
