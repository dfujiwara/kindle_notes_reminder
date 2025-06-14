from src.notebook_parser import NotebookParseResult
from src.repositories.models import Book, Note
import hashlib
from src.repositories.interfaces import BookRepositoryInterface, NoteRepositoryInterface
from typing import Any, TypedDict


class ProcessedNotebookResult(TypedDict):
    book: dict[str, str | int]
    notes: list[dict[str, Any]]


def process_notebook_result(
    result: NotebookParseResult,
    book_repo: BookRepositoryInterface,
    note_repo: NoteRepositoryInterface,
) -> ProcessedNotebookResult:
    # Create a Book instance
    book = Book(title=result.book_title, author=result.authors_str)

    # Add the book to the repository
    book = book_repo.add(book)

    if book.id is None:
        raise ValueError("Book ID is None after adding to repository")

    # Collect notes data
    notes_data: list[dict[str, Any]] = []
    for note_content in result.notes:
        # Generate a stable hash using hashlib
        content_hash = hashlib.sha256(note_content.encode("utf-8")).hexdigest()
        note = Note(content=note_content, content_hash=content_hash, book_id=book.id)
        note = note_repo.add(note)
        notes_data.append(note.model_dump(exclude={"created_at"}))

    return ProcessedNotebookResult(
        book=book.model_dump(exclude={"created_at"}), notes=notes_data
    )
