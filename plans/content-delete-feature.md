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

## Phase 2: Delete Book ✅

Implemented in commit `7fcd309` (PR #172).

- Added `delete_by_note_ids` to `EvaluationRepositoryInterface` and `EvaluationRepository`
- Added `delete_by_book_id` to `NoteRepositoryInterface` and `NoteRepository`
- Added `delete` to `BookRepositoryInterface` and `BookRepository`
- Added `DELETE /books/{book_id}` endpoint (204 No Content, 404 if not found)
- Cascade order: get note IDs → delete evaluations → delete notes → delete book
- Tests in `src/routers/test_books.py`

## Impact on Random & Search

**No code changes needed.** These features query live data:
- `/random` calls `note_repo.get_random()` — deleted notes won't be returned
- `/random/v2` calls `count_with_embeddings()` — counts reflect current state
- `/search` queries embeddings — deleted content won't appear in results
- `find_similar_notes/chunks` — only returns existing records

Deleted content simply disappears from all queries naturally since all queries hit the database at request time.
