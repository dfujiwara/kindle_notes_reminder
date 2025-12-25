"""
Notebook processing endpoints for uploading and parsing Kindle HTML notebooks.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from src.notebook_processing.notebook_parser import (
    parse_notebook_html,
    NotebookParseError,
)
from src.repositories.models import BookWithNoteResponses
from src.repositories.interfaces import (
    BookRepositoryInterface,
    NoteRepositoryInterface,
)
from src.notebook_processing.notebook_processor import process_notebook_result
from src.embedding_interface import EmbeddingClientInterface
from src.dependencies import (
    get_book_repository,
    get_note_repository,
    get_embedding_client,
)

router = APIRouter(tags=["notebooks"])


@router.post(
    "/books",
    summary="Upload Kindle notebook",
    description="""
    Process and store a Kindle HTML notebook file with notes and highlights.

    This endpoint:
    - Parses the uploaded HTML file to extract book metadata and notes
    - Stores the book and notes in the database with deduplication
    - Generates embeddings for semantic search capabilities
    - Returns a summary of the processed content
    """,
    response_description="Processing result with book and notes count",
    responses={
        400: {"description": "Invalid file or parsing error"},
        200: {"description": "Notebook processed successfully"},
    },
)
async def parse_notes(
    file: UploadFile = File(...),
    book_repository: BookRepositoryInterface = Depends(get_book_repository),
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
    embedding_client: EmbeddingClientInterface = Depends(get_embedding_client),
) -> BookWithNoteResponses:
    html_content = await file.read()
    try:
        # Attempt to parse the notebook HTML content
        result = parse_notebook_html(html_content.decode("utf-8"))
    except NotebookParseError as e:
        raise HTTPException(status_code=400, detail=f"Parsing error: {str(e)}")

    # Call the process_notebook_result function
    result = await process_notebook_result(
        result, book_repository, note_repository, embedding_client
    )
    return result
