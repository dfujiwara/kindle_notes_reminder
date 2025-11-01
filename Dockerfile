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

# Copy startup script
COPY scripts/start.sh ./scripts/start.sh
RUN chmod +x ./scripts/start.sh

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Expose port
EXPOSE 8000

# Run startup script (migrations + application)
CMD ["./scripts/start.sh"]