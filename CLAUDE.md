# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

### Core Structure
- **FastAPI Application**: Main application in `src/main.py` with notebook processing and random note endpoints
- **Database Layer**: SQLModel-based models with PostgreSQL and pgvector for embeddings
- **Repository Pattern**: Abstracted data access through repositories (`src/repositories/`)
- **LLM Integration**: OpenAI client for embeddings and text generation

### Key Components
- **Notebook Processing**: Parses HTML notebooks, extracts content, generates embeddings
- **Vector Storage**: Uses pgvector extension for embedding similarity search
- **Database Models**: Book and Note entities with automatic embedding generation
- **Migration System**: Alembic for database schema management

### Data Flow
1. Notebook HTML uploaded via `/notebooks` endpoint
2. Content parsed and processed into Book/Note entities
3. Embeddings generated asynchronously using OpenAI
4. Data stored in PostgreSQL with vector embeddings
5. Random notes retrieved with LLM-generated additional context

### Environment Setup
- Requires `OPENAI_API_KEY` environment variable
- Database URL configurable via `DATABASE_URL`
- Docker Compose provides complete development environment

### Key Files
- `src/main.py` - FastAPI application and endpoints
- `src/repositories/models.py` - SQLModel database models
- `src/notebook_parser.py` - HTML notebook parsing logic
- `src/openai_client.py` - OpenAI API integration
- `compose.yml` - Docker development environment
- `migrations/` - Alembic database migrations
