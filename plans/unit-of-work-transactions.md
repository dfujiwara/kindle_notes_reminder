# Unit of Work: Atomic Transaction Boundaries

## Problem
Repository methods each call `session.commit()` independently. Multi-repository operations (e.g., cascade deletes) risk inconsistent state if a later step fails after earlier ones committed.

## Solution
Move `commit()` out of repositories into `get_session()`, so each HTTP request is a single atomic transaction. Repositories use `flush()` (not `commit()`) when they need generated IDs.

## Changes

### 1. `src/database.py` — commit after yield
```python
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
        session.commit()
```
On exception, Python skips post-yield code; the context manager closes/rolls back the session.

### 2. All repository `add` methods — `commit()` → `flush()`
Files (7 total):
- `src/repositories/book_repository.py`
- `src/repositories/note_repository.py`
- `src/repositories/evaluation_repository.py`
- `src/url_ingestion/repositories/url_repository.py`
- `src/url_ingestion/repositories/urlchunk_repository.py`
- `src/tweet_ingestion/repositories/tweet_repository.py`
- `src/tweet_ingestion/repositories/tweet_thread_repository.py`

Change `self.session.commit()` to `self.session.flush()` (flush sends SQL to get IDs without committing).

### 3. All repository delete/update methods — remove `commit()`
Same 7 files above. Simply delete the `self.session.commit()` line from `delete`, `delete_by_*`, and `update_*` methods.

### 4. Background tasks — own session
Background tasks run after the response (and after `get_session()` commits/closes). They need their own session.

Add to `src/evaluation_service.py`:
```python
async def evaluate_response_background(llm_client, llmInteraction, note):
    with Session(engine) as session:
        repository = EvaluationRepository(session)
        await evaluate_response(llm_client, llmInteraction, repository, note)
        session.commit()
```

Update call sites in:
- `src/routers/notes.py`
- `src/routers/random.py` (2 call sites)

Remove `evaluation_repository` dependency from those endpoint signatures if no longer needed.

### 5. Tests — no changes expected
- Router tests use stub repositories (no real session)
- Repository tests use a shared in-memory SQLite session; flushed data is visible within the same session

## Verification
1. `uv run ruff format && uv run ruff check`
2. `uv run pyright`
3. `uv run pytest -v`
4. Manual: `docker compose up -d`, test cascade delete and URL ingestion
