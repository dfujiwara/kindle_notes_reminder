# Kindle Notes Archive and Notifier

A sophisticated FastAPI application for managing and exploring Kindle notes with AI-powered features. Upload HTML notebook files, perform semantic search across your notes, and get AI-generated additional context for random note discovery.

## Features

- **Notebook Processing**: Parse and extract notes from Kindle HTML notebook exports
- **Vector Database**: PostgreSQL with pgvector extension for semantic similarity search
- **AI Integration**: OpenAI embeddings and LLM for enhanced note exploration
- **Semantic Search**: Find relevant notes using natural language queries
- **Random Note Discovery**: Get random notes with AI-generated additional context
- **Background Processing**: Async LLM evaluation and embedding generation
- **Repository Pattern**: Clean architecture with abstracted data access
- **Docker Support**: Complete development environment with Docker Compose

## Architecture

- **FastAPI**: Modern async web framework with automatic OpenAPI documentation
- **SQLModel**: Type-safe database models with SQLAlchemy integration
- **PostgreSQL + pgvector**: Vector database for embedding storage and similarity search
- **OpenAI API**: Text embeddings (1536 dimensions) and GPT-4 for context generation
- **Alembic**: Database migration management
- **Repository Pattern**: Clean separation of data access logic

## Setup

### Prerequisites

- Python 3.13.2
- Docker and Docker Compose (recommended)
- OpenAI API key

### Environment Variables

Create a `.env` file or set the following environment variable:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### Quick Start with Docker Compose (Recommended)

1. Install Docker and Docker Compose
2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY=your_openai_api_key_here
```
3. Start the services:
```bash
docker compose up -d
```

The application will be available at http://localhost:8000

### Local Development (Alternative)

For local development without Docker:

1. Install uv: `pip install uv`
2. Install dependencies: `uv sync --locked`
3. Set up PostgreSQL with pgvector extension
4. Set `DATABASE_URL` and `OPENAI_API_KEY` environment variables
5. Run migrations: `uv run alembic upgrade head`
6. Start the server: `uv run fastapi dev src/main.py`

## API Documentation

Once running, access the interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check endpoint
- `POST /notebooks` - Upload and process Kindle HTML notebook files
- `GET /books` - List all processed books with note counts
- `GET /books/{book_id}/notes` - Get all notes for a specific book
- `GET /random` - Get a random note with AI-generated additional context and similar notes
- `GET /search?q={query}&limit={limit}` - Semantic search across all notes

## Usage Examples

### Upload a Notebook
```bash
curl -X POST "http://localhost:8000/notebooks" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_kindle_notebook.html"
```

### Search Notes
```bash
curl "http://localhost:8000/search?q=philosophy%20of%20mind&limit=5"
```

### Get Random Note with Context
```bash
curl "http://localhost:8000/random"
```

## Development

### Quality Assurance Commands

```bash
# Format code (run before completing tasks)
uv run ruff format

# Check formatting
uv run ruff format --check

# Lint code
uv run ruff check

# Type checking
uv run pyright

# Run tests
uv run pytest
```

### Database Operations

```bash
# Create new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

### Package Management

```bash
# Add new dependency
uv add package_name

# Add development dependency
uv add --group dev package_name

# Sync dependencies
uv sync --locked
```

## Data Models

### Book
- Title, author, creation timestamp
- One-to-many relationship with notes

### Note
- Content, content hash (for deduplication)
- 1536-dimension OpenAI embedding vector
- Foreign key relationship to book
- One-to-many relationship with evaluations

### Evaluation
- LLM response quality scoring (0.0-1.0)
- Stores prompt, response, analysis, and model information
- Linked to specific notes for quality tracking

## Project Structure

```
src/
├── main.py                 # FastAPI application and endpoints
├── database.py            # Database connection and session management
├── notebook_parser.py     # HTML notebook parsing logic
├── notebook_processor.py  # Business logic for processing parsed notebooks
├── openai_client.py       # OpenAI API integration
├── additional_context.py  # AI context generation for notes
├── evaluations.py         # LLM response evaluation system
├── repositories/          # Data access layer
│   ├── models.py         # SQLModel database models
│   ├── interfaces.py     # Repository interfaces
│   ├── book_repository.py
│   ├── note_repository.py
│   └── evaluation_repository.py
└── test_*.py             # Comprehensive test suite
```

## License

This project is licensed under the terms specified in the LICENSE file.