# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the **Kindle Notes Archive and Notifier** codebase - a sophisticated FastAPI application for managing and exploring Kindle notes with AI-powered features.

## Development Commands

### Package Management
This project uses `uv` for Python package management:
- `uv sync --locked` - Install dependencies from lockfile
- `uv add <package>` - Add new dependency
- `uv run <command>` - Run commands in virtual environment

### Quality Assurance
- `uv run ruff check` - Run linting
- `uv run ruff format` - Format code
- `uv run ruff format --check` - Check formatting without modifying files
- `uv run pyright` - Run type checking
- `uv run pytest` - Run all tests

**IMPORTANT**: Always run `uv run ruff format` before completing any task to ensure consistent code formatting across the codebase.

### Testing
- `uv run pytest` - Run all tests
- `uv run pytest src/test_*.py` - Run specific test files
- `uv run pytest -v` - Verbose test output
- `uv run pytest --cov=src` - Run tests with coverage (if coverage tools are added)

### Database Operations
- `uv run alembic revision --autogenerate -m "description"` - Create new migration
- `uv run alembic upgrade head` - Apply migrations
- `uv run alembic downgrade -1` - Rollback one migration

### Development Server
- `uv run fastapi dev src/main.py` - Run development server with auto-reload
- `uv run uvicorn src.main:app --reload` - Alternative server command

### Docker
- `docker compose up -d` - Start services (app + PostgreSQL with pgvector)
- `docker compose down` - Stop services

## Architecture Overview

### Architectural Principles & Design Decisions

**Repository Pattern**: All database operations are abstracted through repository interfaces (`src/repositories/interfaces.py`). This provides:
- Clean separation of data access logic from business logic
- Easy testing with mock repositories
- Flexibility to change database implementation without affecting business logic

**Dependency Injection**: Uses FastAPI's built-in DI system for:
- Repository instances (`get_book_repository`, `get_note_repository`)
- External service clients (`get_embedding_client`, `get_llm_client`)
- Database sessions (`get_session`)

**Interface Segregation**: Separate interfaces for different concerns:
- `EmbeddingClientInterface` - For generating text embeddings
- `LLMClientInterface` - For LLM text generation
- Repository interfaces for each domain entity

**Type Safety**: Comprehensive typing throughout:
- SQLModel for type-safe database models with automatic validation
- Custom types in `src/types.py` (e.g., `Embedding` type alias)
- Full type hints on all functions and methods

**Domain-Driven Design Elements**:
- Clear domain models (Book, Note, Evaluation) with business logic
- Separation of parsing (`notebook_parser.py`) from processing (`notebook_processor.py`)
- Domain-specific exceptions (`NotebookParseError`)

**Async/Background Processing**: 
- Async endpoint handlers for I/O operations
- Background tasks for LLM evaluation to avoid blocking API responses
- Async embedding generation and database operations

**Content Deduplication**: Uses content hashing to prevent duplicate notes while allowing same content in different books

### Core Structure
- **FastAPI Application**: Main application in `src/main.py` with notebook processing and random note endpoints
- **Database Layer**: SQLModel-based models with PostgreSQL and pgvector for embeddings
- **Repository Pattern**: Abstracted data access through repositories (`src/repositories/`)
- **LLM Integration**: OpenAI client for embeddings and text generation

### Key Components
- **Notebook Processing**: Parses HTML notebooks, extracts content, generates embeddings
- **Vector Storage**: Uses pgvector extension for embedding similarity search (1536 dimensions)
- **Database Models**: Book, Note, and Evaluation entities with relationships
- **Repository Pattern**: Clean abstraction layer with interfaces for data access
- **LLM Integration**: OpenAI GPT-4 for additional context generation
- **Background Processing**: Async LLM evaluation and embedding generation
- **Migration System**: Alembic for database schema management

### Data Flow
1. Notebook HTML uploaded via `/notebooks` endpoint
2. Content parsed and processed into Book/Note entities with content hash deduplication
3. Embeddings generated asynchronously using OpenAI (1536 dimensions)
4. Data stored in PostgreSQL with vector embeddings for similarity search
5. Random notes retrieved with LLM-generated additional context and related notes
6. Search queries converted to embeddings for semantic similarity matching
7. Background tasks evaluate LLM response quality and store evaluations

### Environment Setup
- Requires `OPENAI_API_KEY` environment variable
- Database URL configurable via `DATABASE_URL`
- Optional `CORS_ALLOW_ORIGIN` environment variable for production CORS configuration
- Optional `LOG_LEVEL` environment variable for logging configuration (defaults to INFO)
- Docker Compose provides complete development environment

### Key Files
- `src/main.py` - FastAPI application with router configuration and CORS setup
- `src/routers/` - Modular API endpoint routers organized by domain
  - `general.py` - Health check endpoints
  - `notebooks.py` - Notebook upload and processing
  - `books.py` - Book listing and notes retrieval
  - `notes.py` - Random and specific note retrieval with AI context
  - `search.py` - Semantic search functionality
- `src/repositories/models.py` - SQLModel database models (Book, Note, Evaluation)
- `src/notebook_parser.py` - HTML notebook parsing logic
- `src/notebook_processor.py` - Business logic for processing parsed notebooks
- `src/openai_client.py` - OpenAI API integration (embeddings + LLM)
- `src/additional_context.py` - AI context generation for notes
- `src/evaluations.py` - LLM response evaluation system
- `src/llm_interface.py` - LLM client interface abstraction
- `src/embedding_interface.py` - Embedding client interface abstraction
- `src/dependencies.py` - Dependency injection setup for repositories and clients
- `src/prompts.py` - Prompt templates for LLM interactions
- `src/database.py` - Database connection and session management
- `src/types.py` - Type definitions and custom types
- `compose.yml` - Docker development environment (app + PostgreSQL with pgvector)
- `migrations/` - Alembic database migrations

### API Endpoints
The application provides 8 main endpoints organized across 5 routers:

**General**
- `GET /health` - Health check endpoint

**Notebooks**
- `POST /books` - Upload and process Kindle HTML notebook files

**Books**
- `GET /books` - List all processed books with note counts
- `GET /books/{book_id}/notes` - Get all notes for a specific book

**Notes**
- `GET /random` - Get a random note with AI-generated additional context and similar notes
- `GET /books/{book_id}/notes/{note_id}` - Get a specific note with AI-generated context and related notes

**Search**
- `GET /search?q={query}&limit={limit}` - Semantic search across all notes using embeddings (max limit: 50, similarity threshold: 0.7)
