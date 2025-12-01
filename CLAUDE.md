# CLAUDE.md

FastAPI application for managing Kindle notes with AI-powered features, embeddings, and semantic search.

## Development Commands

**Package Management** (uses `uv`):
- `uv sync --locked` - Install dependencies
- `uv add <package>` - Add dependency
- `uv run <command>` - Run in virtual environment

**Quality Assurance**:
- `uv run ruff check` / `ruff format` - Lint and format code
- `uv run pyright` - Type checking
- `uv run pytest` - Run tests (add `-v` for verbose)
  - Unit tests: `src/test_*.py`
  - Router tests: `src/routers/test_*.py`

**IMPORTANT**: Always run `uv run ruff format` and `uv run pytest` before completing any task.

**Database**:
- `uv run alembic revision --autogenerate -m "description"` - Create migration
- `uv run alembic upgrade head` - Apply migrations

**Development Server**:
- `uv run fastapi dev src/main.py` - Run with auto-reload
- `docker compose up -d` - Start PostgreSQL with pgvector

## Architecture

**Key Patterns**:
- **Repository Pattern**: Database operations abstracted through interfaces (`src/repositories/interfaces.py`)
- **Dependency Injection**: FastAPI DI for repositories, LLM/embedding clients, and database sessions
- **Type Safety**: SQLModel for database models, full type hints throughout
- **Async Processing**: Background tasks for LLM evaluation and embedding generation
- **SSE Streaming**: Server-Sent Events for real-time AI context delivery
- **Content Deduplication**: Content hashing prevents duplicate notes across books

**Stack**:
- FastAPI with SQLModel and PostgreSQL + pgvector (1536-dim embeddings)
- OpenAI for embeddings and GPT-4 context generation
- Alembic for migrations

**Data Flow**:
1. HTML notebook uploaded → parsed into Book/Note entities (hash-deduplicated)
2. Embeddings generated asynchronously → stored in PostgreSQL with pgvector
3. Notes retrieved via SSE streaming → metadata sent first, then AI context chunks
4. LLM context generated and streamed in real-time using Server-Sent Events
5. Related notes found via vector similarity search
6. Background tasks evaluate LLM quality

**Environment Variables**:
- `OPENAI_API_KEY` (required)
- `DATABASE_URL`, `CORS_ALLOW_ORIGIN`, `LOG_LEVEL` (optional)

## Key Files

**Routers** (`src/routers/`): `general.py` (health), `notebooks.py` (upload), `books.py` (listing), `notes.py` (SSE streaming note retrieval), `search.py` (semantic search), `response_builders.py` (response construction)

**Core Logic**: `notebook_parser.py` (HTML parsing), `notebook_processor.py` (business logic), `additional_context.py` (AI generation), `evaluations.py` (quality scoring), `sse_utils.py` (SSE formatting)

**Interfaces**: `llm_interface.py`, `embedding_interface.py`, `repositories/interfaces.py`

**Infrastructure**: `dependencies.py` (DI), `database.py` (sessions), `openai_client.py`, `prompts.py`, `repositories/models.py` (Book, Note, Evaluation)

## API Endpoints

- `GET /health` - Health check
- `POST /books` - Upload Kindle HTML notebook
- `GET /books` - List books with note counts
- `GET /books/{book_id}/notes` - Get all notes for a book
- `GET /random` - Random note with AI context and similar notes (SSE stream)
- `GET /books/{book_id}/notes/{note_id}` - Specific note with AI context (SSE stream)
- `GET /search?q={query}&limit={limit}` - Semantic search (max 50, threshold 0.7)

**SSE Streaming Endpoints** (`/random`, `/books/{book_id}/notes/{note_id}`):
- Returns `text/event-stream` with Server-Sent Events
- Event types: `metadata` (book/note/related notes), `context_chunk` (AI context), `context_complete` (end), `error`
- AI context streams as it generates, improving perceived performance
