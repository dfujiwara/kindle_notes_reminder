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
- `uv run pytest --cov` - Run tests with coverage report
- `uv run pytest --cov --cov-report=html` - Generate HTML coverage report (open with `open htmlcov/index.html`)
  - Unit tests: `src/test_*.py`
  - Router tests: `src/routers/test_*.py`

**IMPORTANT**: Always run `uv run ruff format`, `uv run pyright`, and `uv run pytest` before completing any task.

**Database**:
- `uv run alembic revision --autogenerate -m "description"` - Create migration
- `uv run alembic upgrade head` - Apply migrations

**Development Server** (runs API + PostgreSQL with pgvector):
- `docker compose build --no-cache` - Rebuild images (after dependency changes)
- `docker compose up -d` - Start services in background
- `docker compose logs -f` - View real-time logs
- `docker compose down` - Stop and remove containers

## Architecture

**Key Patterns**:
- **Repository Pattern**: Database operations abstracted through interfaces (`src/repositories/interfaces.py` and `src/url_ingestion/repositories/interfaces.py`)
- **Dependency Injection**: FastAPI DI for repositories, LLM/embedding clients, and database sessions
- **Type Safety**: SQLModel for database models, full type hints throughout
- **Async Processing**: Background tasks for LLM evaluation and embedding generation
- **SSE Streaming**: Server-Sent Events for real-time AI context delivery
- **Content Deduplication**: SHA-256 content hashing prevents duplicates (notes across books, URL chunks within URLs)
- **Unified Content Schema**: Polymorphic response models support both Kindle notes and URL chunks

**Stack**:
- FastAPI with SQLModel and PostgreSQL + pgvector (1536-dim embeddings)
- OpenAI for embeddings and GPT-4 context generation
- Alembic for migrations

**Data Flow**:

**For Kindle Notes:**
1. HTML notebook uploaded → parsed into Book/Note entities (hash-deduplicated)
2. Embeddings generated asynchronously → stored in PostgreSQL with pgvector
3. Notes retrieved via SSE streaming → metadata sent first, then AI context chunks
4. LLM context generated and streamed in real-time using Server-Sent Events
5. Related notes found via vector similarity search
6. Background tasks evaluate LLM quality

**For URL Content:**
1. URL submitted → fetched and parsed with BeautifulSoup (HTML size limit enforced)
2. Content chunked by paragraphs (max 1000 tokens) → summary generated via LLM
3. Embeddings generated in parallel for summary + all chunks (pgvector HNSW index)
4. Summary stored as special chunk (chunk_order=0, is_summary=true)
5. URL chunks retrieved via SSE streaming (same pattern as notes, no evaluation)
6. Related chunks found via vector similarity search

**Environment Variables**:
- `OPENAI_API_KEY` (required)
- `DATABASE_URL`, `CORS_ALLOW_ORIGIN`, `LOG_LEVEL` (optional)

## Key Files

**Routers** (`src/routers/`):
- `general.py` - Health check endpoint
- `notebooks.py` - Kindle notebook upload and processing
- `books.py` - Book listing and management
- `notes.py` - Note SSE streaming, /random, /random/v2 endpoints
- `urls.py` - URL content management endpoints (ingest, list, stream)
- `search.py` - Semantic search across Kindle notes
- `response_builders.py` - Unified response construction for mixed content types
- `random_selector.py` - Weighted random selection between notes and URL chunks

**Notebook Processing** (`src/notebook_processing/`):
- `notebook_parser.py` - HTML parsing for Kindle notebooks
- `notebook_processor.py` - Business logic for note extraction and embedding

**URL Processing** (`src/url_ingestion/`):
- `url_fetcher.py` - HTTP fetching and HTML parsing for URLs
- `content_chunker.py` - Paragraph-based text chunking with size limits
- `url_processor.py` - Complete URL ingestion pipeline (fetch → chunk → summarize → embed)
- `repositories/` - URL and URLChunk data access implementations

**Context Generation** (`src/context_generation/`):
- `additional_context.py` - AI-powered context streaming via LLM

**Core Services**:
- `evaluation_service.py` - Quality scoring for LLM responses (Kindle notes only)
- `sse_utils.py` - Server-Sent Events formatting

**Interfaces**:
- `llm_interface.py`, `embedding_interface.py` - LLM and embedding client contracts
- `repositories/interfaces.py` - Data access layer contracts

**Infrastructure**:
- `dependencies.py` - Dependency injection setup
- `database.py` - Database session management
- `openai_client.py` - OpenAI API integration
- `prompts.py` - LLM prompts and system instructions
- `repositories/models.py` - Database models (Book, Note, URL, URLChunk, Evaluation)

## API Endpoints

### Health & General
- `GET /health` - Health check

### Kindle Notes Management
- `POST /books` - Upload Kindle HTML notebook
- `GET /books` - List books with note counts
- `GET /books/{book_id}/notes` - Get all notes for a book

### URL Content Management
- `POST /urls` - Ingest content from URL (synchronous: fetch → chunk → summarize → embed)
- `GET /urls` - List all ingested URLs with chunk counts
- `GET /urls/{url_id}` - Get URL with all chunks (sorted by order)
- `GET /urls/{url_id}/chunks/{chunk_id}` - Specific chunk with AI context (SSE stream)

### Content Discovery
- `GET /random` - Random Kindle note with AI context (SSE stream)
- `GET /random/v2` - Random content (note or URL chunk) with unified schema (SSE stream)
- `GET /books/{book_id}/notes/{note_id}` - Specific note with AI context (SSE stream)
- `GET /search?q={query}&limit={limit}` - Semantic search across Kindle notes (max 50, threshold 0.7)

**SSE Streaming Endpoints** (`/random`, `/random/v2`, `/books/{book_id}/notes/{note_id}`, `/urls/{url_id}/chunks/{chunk_id}`):
- Returns `text/event-stream` with Server-Sent Events
- Event types: `metadata` (content + related items), `context_chunk` (AI context), `context_complete` (end), `error`
- AI context streams as it generates, improving perceived performance
- Note: `/random/v2` selects between Kindle notes and URL chunks with weighted distribution
- Note: URL chunks do not trigger background evaluation (notes only)

## Testing Patterns

**General Rules**:
- Do not write tests against private functions or methods (prefixed with `_`). Test only the public API surface.



### Router Tests
Router tests use pytest fixtures from `src/routers/conftest.py` to reduce boilerplate and ensure consistent dependency injection patterns.

**Available Fixtures**:
- `setup_book_note_deps()` - Book and note repository dependencies (most common pattern)
- `setup_search_deps()` - Search endpoint dependencies (book, note, embedding client)
- `setup_evaluation_deps()` - Evaluation endpoint dependencies (note, evaluation)
- `setup_url_deps()` - URL endpoint dependencies (URL, URL chunk)
- `setup_notebook_deps()` - Notebook upload dependencies (book, note, embedding, LLM clients)
- `override_dependencies()` - Base fixture for custom dependency configurations

**Usage Example**:
```python
def test_something(setup_book_note_deps):
    book_repo, note_repo = setup_book_note_deps()

    # Add test data
    book = book_repo.add(BookCreate(title="Test", author="Author"))

    # Make request - cleanup is automatic!
    response = client.get("/books")
    assert response.status_code == 200
```

**Benefits**:
- Automatic cleanup via pytest fixtures (no forgotten `finally` blocks)
- Consistent dependency injection across all router tests
- Reduced boilerplate (~125 lines eliminated)
- Single place to modify dependency setup

### Repository Tests
Repository tests use fixtures from `src/repositories/conftest.py` with real repository instances and in-memory SQLite database for integration testing.

### Unit Tests
Unit tests for utilities and helpers live in `src/test_*.py` with direct imports (no dependency injection needed).

## API Testing

**Prerequisites** (docker compose runs both API server and database):
```bash
# 1. Rebuild Docker images (after dependency changes)
docker compose build --no-cache

# 2. Start services in background
docker compose up -d

# 3. Check logs if services fail
docker compose logs -f
```

**Interactive Testing** (uses `/api-test` skill):
- Test individual endpoints with timing metrics
- Group testing by category (Health, Books, URLs, etc.)
- Run all endpoints with summary report
- Automatic data checking and minimal test data creation

**Usage**:
```bash
# Run the skill
/api-test

# Follow interactive prompts to:
# 1. Check existing data
# 2. Create minimal test data if needed
# 3. Select endpoints to test
# 4. View results with status codes and timing
```

**API Test Categories**:
1. **Health & General** - `/health` endpoint
2. **Books & Notes** - Upload, list, retrieve Kindle notes
3. **Random & Discovery** - Random note/content selection
4. **URL Content** - Ingest and retrieve URL content
5. **Search** - Semantic search across notes and chunks

**Example Test Workflow**:
```bash
# 1. Rebuild and start services
docker compose build --no-cache
docker compose up -d

# 2. Check logs if services fail to start
docker compose logs -f

# 3. Run the API test skill
/api-test

# 4. Select endpoints to test and view results
```
