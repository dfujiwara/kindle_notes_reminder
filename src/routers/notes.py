"""
Note-related endpoints for accessing and exploring notes with AI enhancements.
"""

from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from src.repositories.interfaces import (
    BookRepositoryInterface,
    NoteRepositoryInterface,
    EvaluationRepositoryInterface,
)
from src.llm_interface import LLMClientInterface
from src.context_generation.additional_context import (
    get_additional_context_stream,
)
from src.prompts import create_context_prompt, SYSTEM_INSTRUCTIONS
from src.evaluation_service import evaluate_response
from src.sse_utils import format_sse
from src.dependencies import (
    get_book_repository,
    get_note_repository,
    get_evaluation_repository,
    get_llm_client,
)
from src.routers.response_builders import (
    build_note_with_related_notes_response,
    build_unified_response_for_note,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notes"])

# Constants
RELATED_NOTES_LIMIT = 3


@router.get(
    "/random",
    summary="Get random note with streaming AI context",
    description="""
    Retrieve a random note with AI-generated context streamed as Server-Sent Events.

    This endpoint:
    - Selects a random note from the database
    - Streams AI-powered additional context using Server-Sent Events (SSE)
    - Finds related notes based on vector similarity
    - Evaluates the AI response quality in the background

    **SSE Events:**
    - `metadata`: Contains book, note, and related_notes data
    - `context_chunk`: Chunks of AI-generated context as they arrive
    - `context_complete`: Signals the end of streaming
    - `error`: Error information if something goes wrong
    """,
    response_description="Server-Sent Event stream with note data and AI context",
    responses={
        404: {"description": "No notes found in the database"},
        200: {
            "description": "SSE stream with metadata and context chunks",
            "content": {"text/event-stream": {}},
        },
    },
)
async def get_random_note_stream(
    background_tasks: BackgroundTasks,
    book_repository: BookRepositoryInterface = Depends(get_book_repository),
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
    evaluation_repository: EvaluationRepositoryInterface = Depends(
        get_evaluation_repository
    ),
    llm_client: LLMClientInterface = Depends(get_llm_client),
) -> StreamingResponse:
    # Fetch and validate data before streaming
    random_note = note_repository.get_random()
    if not random_note:
        logger.error("Error finding a random note")
        raise HTTPException(status_code=404, detail="No notes found")

    book = book_repository.get(random_note.book_id)
    if not book:
        logger.error(f"Error finding a book with an id of {random_note.book_id}")
        raise HTTPException(status_code=404, detail="Book not found")

    # Find similar notes
    similar_notes = note_repository.find_similar_notes(
        random_note, limit=RELATED_NOTES_LIMIT
    )

    # Prepare metadata using response models for type safety
    metadata = build_note_with_related_notes_response(book, random_note, similar_notes)

    async def event_generator() -> AsyncGenerator[str, None]:
        # Send metadata first
        yield format_sse("metadata", metadata.model_dump(mode="json"))

        # Prepare prompt and instruction
        prompt = create_context_prompt(book.title, random_note.content)
        instruction = SYSTEM_INSTRUCTIONS["context_provider"]

        # Stream context chunks and collect result
        llm_prompt_response = None
        try:
            async for chunk in get_additional_context_stream(
                llm_client, prompt, instruction
            ):
                if chunk.is_complete:
                    # Final result with metadata
                    llm_prompt_response = chunk.llm_prompt_response
                else:
                    # It's a content chunk
                    yield format_sse("context_chunk", {"content": chunk.content})
        except Exception as e:
            logger.error(f"Error streaming context: {e}")
            yield format_sse("error", {"detail": str(e)})
            return

        # Signal completion
        yield format_sse("context_complete", {})

        # Evaluate response in background
        if llm_prompt_response:
            background_tasks.add_task(
                evaluate_response,
                llm_client,
                llm_prompt_response,
                evaluation_repository,
                random_note,
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get(
    "/books/{book_id}/notes/{note_id}",
    summary="Get specific note with streaming AI context",
    description="""
    Retrieve a specific note with AI-generated context streamed as Server-Sent Events.

    This endpoint:
    - Fetches the specified note by book_id and note_id
    - Streams AI-powered additional context using Server-Sent Events (SSE)
    - Finds related notes based on vector similarity
    - Evaluates the AI response quality in the background

    **SSE Events:**
    - `metadata`: Contains book, note, and related_notes data
    - `context_chunk`: Chunks of AI-generated context as they arrive
    - `context_complete`: Signals the end of streaming
    - `error`: Error information if something goes wrong
    """,
    response_description="Server-Sent Event stream with note data and AI context",
    responses={
        404: {"description": "Note not found or doesn't belong to the specified book"},
        200: {
            "description": "SSE stream with metadata and context chunks",
            "content": {"text/event-stream": {}},
        },
    },
)
async def get_note_with_context_stream(
    book_id: int,
    note_id: int,
    background_tasks: BackgroundTasks,
    book_repository: BookRepositoryInterface = Depends(get_book_repository),
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
    evaluation_repository: EvaluationRepositoryInterface = Depends(
        get_evaluation_repository
    ),
    llm_client: LLMClientInterface = Depends(get_llm_client),
) -> StreamingResponse:
    # Fetch and validate data before streaming
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

    # Find similar notes
    similar_notes = note_repository.find_similar_notes(note, limit=RELATED_NOTES_LIMIT)

    # Prepare metadata using response models for type safety
    metadata = build_note_with_related_notes_response(book, note, similar_notes)

    async def event_generator() -> AsyncGenerator[str, None]:
        # Send metadata first
        yield format_sse("metadata", metadata.model_dump(mode="json"))

        # Prepare prompt and instruction
        prompt = create_context_prompt(book.title, note.content)
        instruction = SYSTEM_INSTRUCTIONS["context_provider"]

        # Stream context chunks and collect result
        llm_prompt_response = None
        try:
            async for chunk in get_additional_context_stream(
                llm_client, prompt, instruction
            ):
                if chunk.is_complete:
                    # Final result with metadata
                    llm_prompt_response = chunk.llm_prompt_response
                else:
                    # It's a content chunk
                    yield format_sse("context_chunk", {"content": chunk.content})
        except Exception as e:
            logger.error(f"Error streaming context: {e}")
            yield format_sse("error", {"detail": str(e)})
            return

        # Signal completion
        yield format_sse("context_complete", {})

        # Evaluate response in background
        if llm_prompt_response:
            background_tasks.add_task(
                evaluate_response,
                llm_client,
                llm_prompt_response,
                evaluation_repository,
                note,
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get(
    "/random/v2",
    summary="Get random note with streaming AI context (unified schema)",
    description="""
    Retrieve a random note with AI-generated context streamed as Server-Sent Events.
    Uses the unified response schema (ContentWithRelatedItemsResponse).

    This endpoint:
    - Selects a random note from the database
    - Streams AI-powered additional context using Server-Sent Events (SSE)
    - Finds related notes based on vector similarity
    - Evaluates the AI response quality in the background

    **SSE Events:**
    - `metadata`: Contains source, content, and related_items data (unified schema)
    - `context_chunk`: Chunks of AI-generated context as they arrive
    - `context_complete`: Signals the end of streaming
    - `error`: Error information if something goes wrong
    """,
    response_description="Server-Sent Event stream with unified note data and AI context",
    responses={
        404: {"description": "No notes found in the database"},
        200: {
            "description": "SSE stream with metadata and context chunks",
            "content": {"text/event-stream": {}},
        },
    },
)
async def get_random_content_v2(
    background_tasks: BackgroundTasks,
    book_repository: BookRepositoryInterface = Depends(get_book_repository),
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
    evaluation_repository: EvaluationRepositoryInterface = Depends(
        get_evaluation_repository
    ),
    llm_client: LLMClientInterface = Depends(get_llm_client),
) -> StreamingResponse:
    # Fetch and validate data before streaming
    random_note = note_repository.get_random()
    if not random_note:
        logger.error("Error finding a random note")
        raise HTTPException(status_code=404, detail="No notes found")

    book = book_repository.get(random_note.book_id)
    if not book:
        logger.error(f"Error finding a book with an id of {random_note.book_id}")
        raise HTTPException(status_code=404, detail="Book not found")

    # Find similar notes
    similar_notes = note_repository.find_similar_notes(
        random_note, limit=RELATED_NOTES_LIMIT
    )

    # Use unified response builder
    metadata = build_unified_response_for_note(book, random_note, similar_notes)

    async def event_generator() -> AsyncGenerator[str, None]:
        # Send metadata first
        yield format_sse("metadata", metadata.model_dump(mode="json"))

        # Prepare prompt and instruction
        prompt = create_context_prompt(book.title, random_note.content)
        instruction = SYSTEM_INSTRUCTIONS["context_provider"]

        # Stream context chunks and collect result
        llm_prompt_response = None
        try:
            async for chunk in get_additional_context_stream(
                llm_client, prompt, instruction
            ):
                if chunk.is_complete:
                    # Final result with metadata
                    llm_prompt_response = chunk.llm_prompt_response
                else:
                    # It's a content chunk
                    yield format_sse("context_chunk", {"content": chunk.content})
        except Exception as e:
            logger.error(f"Error streaming context: {e}")
            yield format_sse("error", {"detail": str(e)})
            return

        # Signal completion
        yield format_sse("context_complete", {})

        # Evaluate response in background
        if llm_prompt_response:
            background_tasks.add_task(
                evaluate_response,
                llm_client,
                llm_prompt_response,
                evaluation_repository,
                random_note,
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
