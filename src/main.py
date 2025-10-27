from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import general, notebooks, books, notes, search
from src.cors_config import get_cors_config
import logging
import os

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

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
cors_config = get_cors_config(production_origin=os.getenv("CORS_ALLOW_ORIGIN"))
app.add_middleware(CORSMiddleware, **cors_config)

# Include routers
app.include_router(general.router)
app.include_router(notebooks.router)
app.include_router(books.router)
app.include_router(notes.router)
app.include_router(search.router)
