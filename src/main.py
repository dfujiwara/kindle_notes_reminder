from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from src.notebook_parser import parse_notebook_html, NotebookParseError
from sqlmodel import Session
from src.database import get_session
from src.repositories.note_repository import NoteRepository
from src.repositories.book_repository import BookRepository
from src.notebook_processor import process_notebook_result, ProcessedNotebookResult
from src.additional_context import get_additional_context
from src.openai_client import OpenAIClient, OpenAIEmbeddingClient

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


@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI!"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/notebooks")
async def parse_notebook_endpoint(
    file: UploadFile = File(...), session: Session = Depends(get_session)
) -> ProcessedNotebookResult:
    html_content = await file.read()
    try:
        # Attempt to parse the notebook HTML content
        result = parse_notebook_html(html_content.decode("utf-8"))
    except NotebookParseError as e:
        raise HTTPException(status_code=400, detail=f"Parsing error: {str(e)}")

    # Create repositories
    book_repository = BookRepository(session)
    note_repository = NoteRepository(session)
    embedding_client = OpenAIEmbeddingClient()
    # Call the process_notebook_result function
    result = await process_notebook_result(
        result, book_repository, note_repository, embedding_client
    )
    return result


@app.get("/random")
async def get_random_note_endpoint(session: Session = Depends(get_session)):
    note_repository = NoteRepository(session)
    random_note = note_repository.get_random()
    if not random_note:
        raise HTTPException(status_code=404, detail="No notes found")

    # Find similar notes using vector similarity
    similar_notes = note_repository.find_similar_notes(random_note, limit=3)

    # Use OpenAI client for generating additional context
    llm_client = OpenAIClient()
    additional_context = await get_additional_context(
        llm_client, random_note.book, random_note
    )

    return {
        "book": random_note.book.title,
        "author": random_note.book.author,
        "note": random_note.content,
        "additional_context": additional_context,
        "related_notes": [
            {
                "id": note.id,
                "content": note.content,
            }
            for note in similar_notes
        ],
    }
