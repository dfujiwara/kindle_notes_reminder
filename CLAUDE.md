# CLAUDE.md

FastAPI application for managing Kindle notes with AI-powered features, embeddings, and semantic search.

## Development Commands

This project uses `uv` (not pip/poetry):
- `uv sync --locked` - Install dependencies
- `uv add <package>` - Add dependency
- `uv run <command>` - Run in virtual environment

**IMPORTANT**: Always run `uv run ruff format`, `uv run pyright`, and `uv run pytest` before completing any task.

**Database migrations**: `uv run alembic revision --autogenerate -m "description"` / `uv run alembic upgrade head`

**Dev server**: `docker compose build --no-cache && docker compose up -d`

## Testing Patterns

- Do not write tests against private functions or methods (prefixed with `_`). Test only the public API surface.
- Router tests use pytest fixtures from `src/routers/conftest.py` for dependency injection. See that file for available fixtures (`setup_book_note_deps`, `setup_search_deps`, `setup_url_deps`, etc.).
- Repository tests use fixtures from `src/repositories/conftest.py` with in-memory SQLite.
- Unit tests live in `src/test_*.py` with direct imports.
