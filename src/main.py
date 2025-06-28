from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
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
    title="FastAPI App", description="A sample FastAPI application", version="0.1.0"
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


@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI!"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/notebooks")
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


@app.get("/books/{book_id}/notes")
async def get_notes_by_book(
    book_id: int,
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
):
    # Get all notes for the book
    notes = note_repository.get_by_book_id(book_id)

    return {
        "notes": [
            {"id": note.id, "content": note.content, "created_at": note.created_at}
            for note in notes
        ]
    }


@app.get("/random")
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
