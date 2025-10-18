"""
Note-related endpoints for accessing and exploring notes with AI enhancements.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from src.repositories.models import (
    BookResponse,
    NoteResponse,
    NoteWithContextResponse,
)
from src.repositories.interfaces import (
    BookRepositoryInterface,
    NoteRepositoryInterface,
    EvaluationRepositoryInterface,
)
from src.llm_interface import LLMClientInterface
from src.additional_context import get_additional_context
from src.evaluations import evaluate_response
from src.dependencies import (
    get_book_repository,
    get_note_repository,
    get_evaluation_repository,
    get_llm_client,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notes"])


@router.get(
    "/random",
    summary="Get random note with AI context",
    description="""
    Retrieve a random note enhanced with AI-generated additional context and related notes.

    This endpoint:
    - Selects a random note from the database
    - Generates AI-powered additional context using OpenAI
    - Finds related notes based on vector similarity
    - Evaluates the AI response quality in the background
    """,
    response_description="Random note with AI analysis and similar notes",
    responses={
        404: {"description": "No notes found in the database"},
        200: {"description": "Random note with context retrieved successfully"},
    },
)
async def get_random_note(
    background_tasks: BackgroundTasks,
    book_repository: BookRepositoryInterface = Depends(get_book_repository),
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
    evaluation_repository: EvaluationRepositoryInterface = Depends(
        get_evaluation_repository
    ),
    llm_client: LLMClientInterface = Depends(get_llm_client),
) -> NoteWithContextResponse:
    random_note = note_repository.get_random()
    if not random_note:
        logger.error("Error finding a random note")
        raise HTTPException(status_code=404, detail="No notes found")

    book = book_repository.get(random_note.book_id)
    if not book:
        logger.error(f"Error finding a book with an id of {random_note.book_id}")
        raise HTTPException(status_code=404, detail="No notes found")

    # Find similar notes using vector similarity
    similar_notes = note_repository.find_similar_notes(random_note, limit=3)

    # Use OpenAI client for generating additional context
    additional_context_result = await get_additional_context(
        llm_client, book, random_note
    )

    background_tasks.add_task(
        evaluate_response,
        llm_client,
        additional_context_result,
        evaluation_repository,
        random_note,
    )
    return NoteWithContextResponse(
        book=BookResponse(
            id=book.id,
            title=book.title,
            author=book.author,
            created_at=book.created_at,
        ),
        note=NoteResponse(
            id=random_note.id,
            content=random_note.content,
            created_at=random_note.created_at,
        ),
        additional_context=additional_context_result.response,
        related_notes=[
            NoteResponse(
                id=note.id,
                content=note.content,
                created_at=note.created_at,
            )
            for note in similar_notes
        ],
    )


@router.get(
    "/books/{book_id}/notes/{note_id}",
    summary="Get specific note with AI context",
    description="""
    Retrieve a specific note enhanced with AI-generated additional context and related notes.

    This endpoint:
    - Fetches the specified note by book_id and note_id
    - Generates AI-powered additional context using OpenAI
    - Finds related notes based on vector similarity
    - Evaluates the AI response quality in the background
    """,
    response_description="Specific note with AI analysis and similar notes",
    responses={
        404: {"description": "Note not found or doesn't belong to the specified book"},
        200: {"description": "Note with context retrieved successfully"},
    },
)
async def get_note_with_context(
    book_id: int,
    note_id: int,
    background_tasks: BackgroundTasks,
    book_repository: BookRepositoryInterface = Depends(get_book_repository),
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
    evaluation_repository: EvaluationRepositoryInterface = Depends(
        get_evaluation_repository
    ),
    llm_client: LLMClientInterface = Depends(get_llm_client),
) -> NoteWithContextResponse:
    # Get the specific note, ensuring it belongs to the specified book
    note = note_repository.get(book_id=book_id, note_id=note_id)
    if not note:
        logger.error(
            f"Error finding a note with an id of {note_id} in a book of {book_id}"
        )
        raise HTTPException(
            status_code=404,
            detail="Note not found or doesn't belong to the specified book",
        )

    book = book_repository.get(book_id)
    if not book:
        logger.error(f"Error finding a book with an id of {book_id}")
        raise HTTPException(status_code=404, detail="Book not found")

    # Find similar notes using vector similarity
    similar_notes = note_repository.find_similar_notes(note, limit=3)

    # Use OpenAI client for generating additional context
    additional_context_result = await get_additional_context(llm_client, book, note)

    # Add evaluation task using consolidated function
    background_tasks.add_task(
        evaluate_response,
        llm_client,
        additional_context_result,
        evaluation_repository,
        note,
    )
    return NoteWithContextResponse(
        book=BookResponse(
            id=book.id, title=book.title, author=book.author, created_at=book.created_at
        ),
        note=NoteResponse(id=note.id, content=note.content, created_at=note.created_at),
        additional_context=additional_context_result.response,
        related_notes=[
            NoteResponse(
                id=similar_note.id,
                content=similar_note.content,
                created_at=similar_note.created_at,
            )
            for similar_note in similar_notes
        ],
    )
