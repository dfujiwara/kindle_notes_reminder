from src.notebook_parser import NotebookParseResult
from src.repositories.models import BookCreate, Note
import hashlib
from src.repositories.interfaces import BookRepositoryInterface, NoteRepositoryInterface
from typing import Any, TypedDict
from src.embedding_interface import EmbeddingClientInterface
import asyncio
import logging

# Configure logging
logger = logging.getLogger(__name__)


class ProcessedNotebookResult(TypedDict):
    book: dict[str, str | int]
    notes: list[dict[str, Any]]


async def process_notebook_result(
    result: NotebookParseResult,
    book_repo: BookRepositoryInterface,
    note_repo: NoteRepositoryInterface,
    embedding_client: EmbeddingClientInterface,
) -> ProcessedNotebookResult:
    # Create a BookCreate instance
    book_create = BookCreate(title=result.book_title, author=result.authors_str)

    # Add the book to the repository
    book = book_repo.add(book_create)

    # Generate embeddings for all notes in parallel
    logger.info(f"Generating embeddings for {len(result.notes)} notes")
    try:
        embedding_tasks = [
            embedding_client.generate_embedding(note_content)
            for note_content in result.notes
        ]
        embeddings = await asyncio.gather(*embedding_tasks)
        logger.info("Successfully generated all embeddings")
    except Exception as e:
        logger.error(f"Error during parallel embedding generation: {str(e)}")
        raise

    # Create and save notes with their embeddings
    notes_data: list[dict[str, Any]] = []
    for note_content, embedding in zip(result.notes, embeddings):
        # Generate a stable hash using hashlib
        content_hash = hashlib.sha256(note_content.encode("utf-8")).hexdigest()

        # Create note with embedding
        note = Note(
            content=note_content,
            content_hash=content_hash,
            book_id=book.id,
            embedding=embedding,
        )
        note = note_repo.add(note)
        notes_data.append(note.model_dump(exclude={"created_at", "embedding"}))

    return ProcessedNotebookResult(
        book=book.model_dump(exclude={"created_at"}), notes=notes_data
    )
