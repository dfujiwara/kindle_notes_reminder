# Content Delete Feature Plan

## Overview
DELETE endpoints for URLs (Phase 1) and Books (Phase 2). The main challenge is managing cascading relationships since **no FK cascade deletes are configured** in the database.

## Relationship Chains
- **URL** → URLChunk (1:N, FK `urlchunk.url_id → url.id`)
- **Book** → Note (1:N, FK `note.book_id → book.id`) → Evaluation (1:N, FK `evaluation.note_id → note.id`)

## Approach: Application-level cascade delete
Delete children first, then parent, all within a single database transaction. No migration needed — handle it in the repository layer.

### Why not add DB-level CASCADE?
A migration to add `ON DELETE CASCADE` is possible but would require an `ALTER TABLE` on production. The app-level approach is simpler, equally safe within a transaction, and avoids a migration.

## Phase 1: Delete URL ✅

Implemented in commit `b1e5653` (PR #171).

- Added `delete_by_url_id` to `URLChunkRepositoryInterface` and `URLChunkRepository`
- Added `DELETE /urls/{url_id}` endpoint (204 No Content, 404 if not found)
- Deletes chunks first, then URL (transactional via shared session)
- Tests in `src/routers/test_urls.py`

## Phase 2: Delete Book (TODO)

### 1. Add `delete_by_note_ids` to `EvaluationRepositoryInterface`
**File:** `src/repositories/interfaces.py`
- Add: `def delete_by_note_ids(self, note_ids: list[int]) -> None: ...`

### 2. Implement in `EvaluationRepository`
**File:** `src/repositories/evaluation_repository.py`
- Bulk delete evaluations for given note IDs

### 3. Add `delete_by_book_id` to `NoteRepositoryInterface`
**File:** `src/repositories/interfaces.py`
- Add: `def delete_by_book_id(self, book_id: int) -> list[int]: ...` (returns note IDs for evaluation cleanup)

### 4. Implement in `NoteRepository`
**File:** `src/repositories/note_repository.py`
- Query note IDs for book, then bulk delete

### 5. Add DELETE endpoint
**File:** `src/routers/books.py`
- `DELETE /books/{book_id}` → 204 No Content
- Inject `book_repo`, `note_repo`, `evaluation_repo`
- Verify book exists (404 if not)
- Get note IDs for book → delete evaluations → delete notes → delete book

### 6. Tests
**File:** `src/routers/test_books.py`
- Test successful delete with cascading cleanup
- Test 404 for non-existent book

## Impact on Random & Search

**No code changes needed.** These features query live data:
- `/random` calls `note_repo.get_random()` — deleted notes won't be returned
- `/random/v2` calls `count_with_embeddings()` — counts reflect current state
- `/search` queries embeddings — deleted content won't appear in results
- `find_similar_notes/chunks` — only returns existing records

Deleted content simply disappears from all queries naturally since all queries hit the database at request time.

## Remaining Files to Modify (Phase 2)
| File | Change |
|------|--------|
| `src/repositories/interfaces.py` | Add `delete_by_note_ids` to Evaluation, `delete_by_book_id` to Note |
| `src/repositories/evaluation_repository.py` | Implement `delete_by_note_ids` |
| `src/repositories/note_repository.py` | Implement `delete_by_book_id` |
| `src/routers/books.py` | Add `DELETE /books/{book_id}` |
| `src/routers/test_books.py` | Delete book tests |

## Verification
1. `uv run ruff format && uv run ruff check`
2. `uv run pyright`
3. `uv run pytest`
4. Manual: `docker compose up -d` then `/api-test` to verify delete endpoints
