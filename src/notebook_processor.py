from src.notebook_parser import NotebookParseResult
from src.repositories.models import (
    BookCreate,
    NoteCreate,
    NoteResponse,
    BookResponse,
    BookWithNoteResponses,
)
import hashlib
from src.repositories.interfaces import BookRepositoryInterface, NoteRepositoryInterface
from src.embedding_interface import EmbeddingClientInterface
import asyncio
import logging

# Configure logging
logger = logging.getLogger(__name__)


async def process_notebook_result(
    result: NotebookParseResult,
    book_repo: BookRepositoryInterface,
    note_repo: NoteRepositoryInterface,
    embedding_client: EmbeddingClientInterface,
) -> BookWithNoteResponses:
    # Create a BookCreate instance
    book_create = BookCreate(title=result.book_title, author=result.authors_str)

    # Add the book to the repository
    book = book_repo.add(book_create)
    book_response = BookResponse.model_validate(book)

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
    notes: list[NoteResponse] = []
    for note_content, embedding in zip(result.notes, embeddings):
        # Generate a stable hash using hashlib
        content_hash = hashlib.sha256(note_content.encode("utf-8")).hexdigest()

        # Create note with embedding
        note = NoteCreate(
            content=note_content,
            content_hash=content_hash,
            book_id=book.id,
            embedding=embedding,
        )
        note = note_repo.add(note)
        notes.append(NoteResponse.model_validate(note))

    logger.info("Successfully generated the processed book result")
    return BookWithNoteResponses(book=book_response, notes=notes)
