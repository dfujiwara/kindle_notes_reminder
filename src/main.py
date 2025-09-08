from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Any
from src.notebook_parser import parse_notebook_html, NotebookParseError
from sqlmodel import Session
from src.database import get_session
from src.repositories.evaluation_repository import EvaluationRepository
from src.repositories.models import Evaluation
from src.repositories.note_repository import NoteRepository
from src.repositories.book_repository import BookRepository
from src.repositories.interfaces import (
    BookRepositoryInterface,
    EvaluationRepositoryInterface,
    NoteRepositoryInterface,
)
from src.notebook_processor import process_notebook_result, ProcessedNotebookResult
from src.additional_context import get_additional_context
from src.openai_client import OpenAIClient, OpenAIEmbeddingClient
from src.embedding_interface import EmbeddingClientInterface
from src.llm_interface import LLMClientInterface, LLMPromptResponse
from src.evaluations import evaluate_llm_response

app = FastAPI(
    title="Kindle Notes Archive and Notifier",
    description="""
    A sophisticated FastAPI application for managing and exploring Kindle notes with AI-powered features.

    ## Features

    * **Notebook Processing**: Upload and parse Kindle HTML notebook files
    * **Smart Organization**: Automatic book and note extraction with deduplication
    * **AI-Powered Context**: Generate additional insights for your notes using OpenAI
    * **Vector Search**: Semantic search across all your notes using embeddings
    * **Related Notes**: Find similar notes based on content similarity
    * **Background Processing**: Asynchronous LLM evaluation and embedding generation

    ## Getting Started

    1. Upload your Kindle notebook HTML files via `/notebooks`
    2. Browse your books and notes via `/books`
    3. Get AI-enhanced random notes via `/random`
    4. Search semantically across all notes via `/search`
    """,
    version="1.0.0",
    contact={
        "name": "Kindle Notes API",
        "url": "https://github.com/dfujiwara/kindle_notes_reminder",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "general",
            "description": "General endpoints for health checks and basic info",
        },
        {
            "name": "notebooks",
            "description": "Upload and process Kindle HTML notebook files",
        },
        {
            "name": "books",
            "description": "Browse and manage your book collection",
        },
        {
            "name": "notes",
            "description": "Access and explore your notes with AI enhancements",
        },
        {
            "name": "search",
            "description": "Semantic search across all your notes using AI embeddings",
        },
    ],
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency functions for repositories
def get_book_repository(
    session: Session = Depends(get_session),
) -> BookRepositoryInterface:
    return BookRepository(session)


def get_note_repository(
    session: Session = Depends(get_session),
) -> NoteRepositoryInterface:
    return NoteRepository(session)


def get_evaluation_repository(
    session: Session = Depends(get_session),
) -> EvaluationRepositoryInterface:
    return EvaluationRepository(session)


def get_embedding_client() -> EmbeddingClientInterface:
    return OpenAIEmbeddingClient()


def get_llm_client() -> LLMClientInterface:
    return OpenAIClient()


@app.get(
    "/health",
    tags=["general"],
    summary="Health check",
    description="Check if the API service is running and healthy",
    response_description="Health status",
)
async def health_check():
    return {"status": "healthy"}


@app.post(
    "/notebooks",
    tags=["notebooks"],
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
async def parse_notebook_endpoint(
    file: UploadFile = File(...),
    book_repository: BookRepositoryInterface = Depends(get_book_repository),
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
    embedding_client: EmbeddingClientInterface = Depends(get_embedding_client),
) -> ProcessedNotebookResult:
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


@app.get(
    "/books",
    tags=["books"],
    summary="List all books",
    description="Retrieve all processed books with their note counts",
    response_description="List of books with metadata and note counts",
)
async def get_books(
    book_repository: BookRepositoryInterface = Depends(get_book_repository),
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
):
    books = book_repository.list_books()
    note_count_dict = note_repository.get_note_counts_by_book_ids(
        [b.id for b in books if b.id is not None]
    )
    return {
        "books": [
            {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "note_count": note_count_dict.get(book.id, 0) if book.id else 0,
            }
            for book in books
        ]
    }


@app.get(
    "/books/{book_id}/notes",
    tags=["books", "notes"],
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
        raise HTTPException(status_code=404, detail="Book not found")

    # Get all notes for the book
    notes = note_repository.get_by_book_id(book_id)

    return {
        "book": {
            "id": book.id,
            "title": book.title,
            "author": book.author,
        },
        "notes": [
            {"id": note.id, "content": note.content, "created_at": note.created_at}
            for note in notes
        ],
    }


@app.get(
    "/random",
    tags=["notes"],
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
async def get_random_note_endpoint(
    background_tasks: BackgroundTasks,
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
    evaluation_repository: EvaluationRepositoryInterface = Depends(
        get_evaluation_repository
    ),
    llm_client: LLMClientInterface = Depends(get_llm_client),
):
    random_note = note_repository.get_random()
    if not random_note:
        raise HTTPException(status_code=404, detail="No notes found")

    # Find similar notes using vector similarity
    similar_notes = note_repository.find_similar_notes(random_note, limit=3)

    # Use OpenAI client for generating additional context
    additional_context_result = await get_additional_context(
        llm_client, random_note.book, random_note
    )

    async def evaluate_response(
        llmInteraction: LLMPromptResponse, repository: EvaluationRepositoryInterface
    ):
        result = await evaluate_llm_response(
            llm_client, llmInteraction.prompt, llmInteraction.response
        )
        note_id = random_note.id
        if not note_id:
            raise AssertionError("Random note ID should always be set at this point")
        evaluation = Evaluation(
            prompt=llmInteraction.prompt,
            response=llmInteraction.response,
            score=result[0],
            analysis=result[1],
            note_id=note_id,
        )
        repository.add(evaluation)

    background_tasks.add_task(
        evaluate_response, additional_context_result, evaluation_repository
    )
    return {
        "book": random_note.book.title,
        "author": random_note.book.author,
        "note": random_note.content,
        "additional_context": additional_context_result.response,
        "related_notes": [
            {
                "id": note.id,
                "content": note.content,
            }
            for note in similar_notes
        ],
    }


@app.get(
    "/search",
    tags=["search"],
    summary="Semantic search across notes",
    description="""
    Search for notes using semantic search based on the provided query.

    This endpoint:
    - Converts your search query into embeddings using OpenAI
    - Finds semantically similar notes using vector similarity
    - Groups results by book for better organization
    - Returns results with similarity scores above the threshold
    """,
    response_description="Search results grouped by book with similarity scores",
    responses={
        200: {"description": "Search completed successfully"},
        422: {"description": "Invalid query parameters"},
    },
)
async def search_notes(
    q: str,
    limit: int = 10,
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
    embedding_client: EmbeddingClientInterface = Depends(get_embedding_client),
) -> dict[str, Any]:
    # Validate limit
    limit = min(limit, 50)

    # Generate embedding for the search query
    query_embedding = await embedding_client.generate_embedding(q)

    # Search for similar notes
    similar_notes = note_repository.search_notes_by_embedding(
        query_embedding, limit=limit, similarity_threshold=0.7
    )

    # Group notes by book
    books_dict: dict[int, dict[str, Any]] = {}

    for note in similar_notes:
        book_id = note.book.id
        if book_id is None:
            continue
        if book_id not in books_dict:
            books_dict[book_id] = {
                "book": {
                    "id": note.book.id,
                    "title": note.book.title,
                    "author": note.book.author,
                },
                "notes": [],
            }

        books_dict[book_id]["notes"].append(
            {
                "id": note.id,
                "content": note.content,
            }
        )

    results = list(books_dict.values())
    total_notes = sum(len(book["notes"]) for book in results)

    return {"query": q, "results": results, "count": total_notes}
