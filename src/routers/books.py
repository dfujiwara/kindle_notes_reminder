"""
Book-related endpoints for browsing and managing the book collection.
"""

from fastapi import APIRouter, Depends, HTTPException
from src.repositories.models import (
    BookResponse,
    BookWithNotesResponse,
    NoteResponse,
)
from src.repositories.interfaces import (
    BookRepositoryInterface,
    NoteRepositoryInterface,
)
from src.dependencies import get_book_repository, get_note_repository
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["books"])


@router.get(
    "/books",
    summary="List all books",
    description="Retrieve all processed books with their note counts",
    response_description="List of books with metadata and note counts",
)
async def get_books(
    book_repository: BookRepositoryInterface = Depends(get_book_repository),
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
):
    books = book_repository.list_books()
    note_count_dict = note_repository.get_note_counts_by_book_ids([b.id for b in books])
    book_responses: list[BookWithNotesResponse] = []
    for book in books:
        book_responses.append(
            BookWithNotesResponse(
                id=book.id,
                title=book.title,
                author=book.author,
                created_at=book.created_at,
                note_count=note_count_dict.get(book.id, 0),
            )
        )
    return {"books": book_responses}


@router.get(
    "/books/{book_id}/notes",
    summary="Get notes for a specific book",
    description="Retrieve all notes for a given book ID along with book metadata",
    response_description="Book information and list of associated notes",
    responses={
        404: {"description": "Book not found"},
        200: {"description": "Book and notes retrieved successfully"},
    },
)
async def get_notes_by_book(
    book_id: int,
    book_repository: BookRepositoryInterface = Depends(get_book_repository),
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
):
    book = book_repository.get(book_id)
    if not book:
        logger.error(f"Error finding a book with an id of {book_id}")
        raise HTTPException(status_code=404, detail="Book not found")

    # Get all notes for the book
    notes = note_repository.get_by_book_id(book_id)

    return {
        "book": BookResponse(
            id=book.id,
            title=book.title,
            author=book.author,
            created_at=book.created_at,
        ),
        "notes": [
            NoteResponse(id=note.id, content=note.content, created_at=note.created_at)
            for note in notes
        ],
    }
