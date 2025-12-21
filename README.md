# Kindle Notes Reminder

A FastAPI application for managing and exploring Kindle notes with AI-powered semantic search and context generation.

## Features

- Parse Kindle HTML notebook exports
- Semantic search using OpenAI embeddings and pgvector
- Random note discovery with AI-generated context
- Clean architecture with repository pattern
- Docker support for easy setup

## Stack

FastAPI • PostgreSQL + pgvector • OpenAI API • SQLModel • Alembic

## Quick Start

**Prerequisites**: Docker, Docker Compose, and an OpenAI API key

1. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY=your_openai_api_key_here
   ```

2. Start the application:
   ```bash
   docker compose up -d
   ```

3. Access the API at http://localhost:8000 (docs at http://localhost:8000/docs)

## Usage

Upload a Kindle notebook:
```bash
curl -X POST "http://localhost:8000/notebooks" \
  -F "file=@your_kindle_notebook.html"
```

Search your notes:
```bash
curl "http://localhost:8000/search?q=your+query&limit=5"
```

Get a random note with AI context:
```bash
curl "http://localhost:8000/random"
```

## Development

Local setup (without Docker):
```bash
# Install dependencies
pip install uv
uv sync --locked

# Run migrations
uv run alembic upgrade head

# Start dev server
uv run fastapi dev src/main.py
```

Common commands:
```bash
uv run ruff format          # Format code
uv run ruff check           # Lint
uv run pyright              # Type check
uv run pytest               # Run tests
```

See [CLAUDE.md](CLAUDE.md) for detailed development guidelines and architecture documentation.