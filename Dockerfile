# Single stage: Build and runtime
FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy pyproject.toml and uv.lock
COPY pyproject.toml uv.lock ./

# Create venv and sync with lock file
RUN uv venv && \
    . .venv/bin/activate && \
    uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/

# Copy migration files
COPY alembic.ini ./
COPY migrations/ ./migrations/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]