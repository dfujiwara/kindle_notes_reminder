# URL Content Ingestion Feature - Implementation Plan

## Overview

Add capability to ingest content from URLs, chunk it for searchability, generate summaries, and serve it through the existing API infrastructure alongside Kindle notes.

## Current Architecture Understanding

**Key Components Explored:**

- **Data Models** (`src/repositories/models.py`):
  - Book (1:N) → Note relationship
  - Note: content, content_hash (SHA-256), embedding (1536D), book_id FK
  - Unique constraints: Book on (title, author), Note on content_hash
  - HNSW vector index on embeddings for similarity search

- **API Patterns** (`src/routers/notes.py`):
  - SSE streaming endpoints: `/random`, `/books/{book_id}/notes/{note_id}`
  - Event types: `metadata`, `context_chunk`, `context_complete`, `error`
  - Metadata sent first, then AI context streamed incrementally
  - Background evaluation tasks for LLM quality scoring

- **Processing Pipeline**:
  - HTML upload → parse → parallel embedding generation → hash-based deduplication → store
  - Async embedding generation with `asyncio.gather()`
  - Background tasks for LLM evaluation after streaming completes

## Confirmed Implementation Decisions

Based on user requirements, the following design decisions are confirmed:

1. **Processing Model**: ✓ **Synchronous** - `POST /urls` blocks until fetching, chunking, embedding, and summary generation complete. Simpler error handling, immediate user feedback.

2. **Duplicate URL Handling**: ✓ **Return existing URL** - Deduplicate by URL and return existing record without re-fetching. Fast and prevents duplicate work.

3. **Content Restrictions**: ✓ **Max content size limit** - Reject URLs with content exceeding size limit (500KB HTML default via `settings.max_url_content_size`). Prevents abuse and excessive storage.

4. **Quality Evaluation**: ✓ **Skip evaluation for URL chunks** - Only evaluate Kindle notes with background LLM tasks. Simpler, lower cost. URL content quality less critical than note context quality.

## Design Decisions

### 1. Data Model: Separate URL/URLChunk Models ✓

**Decision:** Create new `URL` and `URLChunk` models, separate from `Book` and `Note`.

**Rationale:**
- Clean separation of concerns
- Different metadata requirements (chunk_order, is_summary, url, etc.)
- Avoid schema pollution and foreign key conflicts
- Each model can evolve independently
- Clear semantics (no confusion between "notes" and "chunks")

**Models:**
```python
URL:
  - id, url (unique), title, fetched_at, created_at
  - Unique constraint on url

URLChunk:
  - id, content, content_hash (unique), url_id (FK), chunk_order, is_summary
  - embedding (Vector 1536), created_at
  - Unique constraint on content_hash
  - HNSW index on embedding
```

### 2. Unified `/random` Endpoint ✓

**Decision:** Modify `/random` to return either Kindle notes OR URL chunks.

**Rationale:**
- Better user experience - "serendipity" across all content
- Single endpoint for clients to consume
- Promotes discovery of URL content alongside Kindle highlights

### 3. Application-Level Random Selection ✓

**Decision:** Randomly choose between tables at application level (not SQL UNION).

**Implementation Strategy:**
```python
# Weighted random based on counts
note_count = note_repo.count_with_embeddings()
chunk_count = url_chunk_repo.count_with_embeddings()
total = note_count + chunk_count

rand = random.randint(0, total - 1)
if rand < note_count:
    # Fetch and return random note
else:
    # Fetch and return random URL chunk
```

**Benefits:**
- Simple, no complex SQL
- Easy to test and maintain
- Can cache counts for performance
- Clear control flow

### 4. Unified Response Schema ✓

**Decision:** Create normalized schema that both content types map to.

**Schema:**
```python
SourceResponse:
  - id, title, type ("book" | "url")
  - author (optional, books only)
  - url (optional, URLs only)
  - created_at

ContentItemResponse:
  - id, content_type, content, created_at
  - is_summary (optional, URL chunks only)
  - chunk_order (optional, URL chunks only)

ContentWithRelatedItemsResponse:
  - source: SourceResponse
  - content: ContentItemResponse
  - related_items: list[ContentItemResponse]
```

**Benefits:**
- Consistent client experience
- Type discrimination via `content_type` field
- Both types fit naturally

### 5. Shared SSE Streaming Infrastructure ✓

**Decision:** Reuse existing SSE streaming pattern for URL chunks.

**Approach:**
- Same event types: `metadata`, `context_chunk`, `context_complete`, `error`
- Response builders map each type to unified schema
- AI context generation adapts prompts for URL content
- Same background evaluation pattern

## Finalized Design Decisions

### A. URL Content Fetching ✓
- **Decision:** Full HTML text extraction using BeautifulSoup with content size limit
- **Implementation:**
  - Use `httpx` for async HTTP requests (30s timeout, follow redirects)
  - BeautifulSoup4 for HTML parsing
  - **Content size check:** Reject if HTML exceeds `settings.max_url_content_size` (default 500KB)
  - Extract all text content from HTML body
  - Handle timeouts, connection errors, and HTTP errors
  - Store original URL for reference

### B. Chunking Strategy ✓
- **Decision:** Paragraph-based chunking with max size limit
- **Implementation:**
  - Split content by paragraphs (double newline or `<p>` tags)
  - Set max chunk size (e.g., 1000 tokens/~4000 characters)
  - If paragraph exceeds max, split by sentences within max size
  - Preserve chunk order via `chunk_order` field
  - Maintain natural reading boundaries where possible

### C. Summary Storage ✓
- **Decision:** Store summary as special URLChunk with `is_summary=True` flag
- **Implementation:**
  - Summary stored as first chunk (chunk_order=0, is_summary=True)
  - Generated via LLM after chunking complete
  - Can be queried like any chunk
  - Enables consistent retrieval patterns

### D. Embedding Strategy ✓
- **Decision:** Generate embeddings for BOTH chunks AND summary
- **Implementation:**
  - Each chunk gets embedding (including summary chunk)
  - Parallel generation using `asyncio.gather()` (like notes)
  - All chunks searchable via semantic search
  - Summary chunk enables URL-level discovery
  - Same 1536D OpenAI embeddings as notes

### E. Additional Endpoints
- **Required endpoints:**
  - `POST /urls` - Ingest URL content (with background processing)
  - `GET /urls` - List ingested URLs with chunk counts
  - `GET /urls/{url_id}` - Get URL details with all chunks
  - `GET /urls/{url_id}/chunks/{chunk_id}` - Specific chunk with SSE streaming
  - Update `GET /random` - Unified random (notes + URL chunks)
  - Update `GET /search` - Include URL chunks in semantic search

## Implementation Plan

### Phase 1: Database Models & Migration (Foundation) - ⚠️ MOSTLY COMPLETE (migration only blocker)

**1.1 Add Models to `src/repositories/models.py`:** ✅ COMPLETE
- ✅ `URL` model: `id, url (unique), title, fetched_at, created_at` (commit b060b83)
- ✅ `URLChunk` model: `id, content, content_hash (unique), url_id (FK), chunk_order, is_summary, embedding (Vector 1536), created_at` (commit b060b83)
- ✅ Unified response models (discriminated unions using `Literal`):
  - `BookSource` and `URLSource` (with `type: Literal["book"]` or `Literal["url"]`)
  - `NoteContent` and `URLChunkContent` (with `content_type: Literal["note"]` or `Literal["url_chunk"]`)
  - `ContentWithRelatedItemsResponse` (unified response combining source + content + related items)

**1.2 Create Migration:** ✅ COMPLETE
- ✅ Migration file: `migrations/versions/fb012279fd22_add_url_and_urlchunk_tables.py` (auto-generated)
- ✅ Fixed HNSW index creation:
  - Issue: Initial Alembic API didn't support operator class specification → Alembic hung
  - Solution: Used raw SQL with explicit `vector_cosine_ops` operator class
  - Pattern: Matches existing note embedding index (dbff8ad5086d migration)
- ✅ Foreign key constraint: url_id → URL.id
- ✅ Unique constraints: url field, content_hash field
- **Ready to apply:** `uv run alembic upgrade head`

**1.3 Add Repository Interfaces to `src/repositories/interfaces.py`:** ✅ COMPLETE (commit 4f3df43)
- ✅ `URLRepositoryInterface` with methods: add, get, get_by_url, list_urls, delete
- ✅ `URLChunkRepositoryInterface` with methods: add, get, get_random, find_similar_chunks, search_chunks_by_embedding, get_chunk_counts_by_url_ids, count_with_embeddings
- ✅ `count_with_embeddings()` added to both NoteRepository and URLChunkRepository interfaces

### Phase 2: Repository Implementations - ✅ COMPLETE (commit 02b37bc)

**2.1 Create `src/repositories/url_repository.py`:** ✅ COMPLETE
- ✅ Pattern: Mirror `BookRepository` structure
- ✅ Key feature: Deduplication by URL in `add()` method

**2.2 Create `src/repositories/urlchunk_repository.py`:** ✅ COMPLETE
- ✅ Pattern: Mirror `NoteRepository` structure
- ✅ Key features:
  - Deduplication by `content_hash` in `add()`
  - Vector similarity search: `find_similar_chunks()`, `search_chunks_by_embedding()`
  - Random selection: `get_random()` using `func.random()`

### Phase 3: URL Fetching & Content Processing - ✅ COMPLETE (commit TBD)

**3.1 Create `src/url_ingestion/url_fetcher.py`:** ✅ COMPLETE
- ✅ Function: `async fetch_url_content(url: str) -> FetchedContent`
- ✅ Use `httpx.AsyncClient` for HTTP requests (timeout: 30s, follow redirects)
- ✅ Use `BeautifulSoup` to parse HTML and extract text
- ✅ Remove script/style/nav/footer/header tags
- ✅ Clean excessive whitespace
- ✅ Extract title from `<title>` tag
- ✅ Raise `URLFetchError` on failures
- ✅ Tests: 20/20 passing

**3.2 Create `src/url_ingestion/content_chunker.py`:** ✅ COMPLETE
- ✅ Function: `chunk_text_by_paragraphs(text: str, max_chunk_size: int = 1000) -> list[TextChunk]`
- ✅ Split by double newlines (paragraphs)
- ✅ Combine small paragraphs up to max size
- ✅ Split large paragraphs if they exceed max size
- ✅ Return chunks with content, SHA-256 hash, and order
- ✅ Tests: 13/13 passing

**3.3 Create `src/url_ingestion/url_processor.py`:** ✅ COMPLETE
- ✅ Pattern: Mirror `notebook_processor.py` structure
- ✅ Function: `async process_url_content(...) -> URLWithChunksResponse`
- ✅ **Processing:** Synchronous (blocks until complete)
- ✅ Steps:
  1. **Check if URL exists** → return existing URL with chunks if found (no re-fetching)
  2. Fetch URL content with `fetch_url_content()` (enforces size limit)
  3. Chunk content using `chunk_text_by_paragraphs(max_chunk_size=1000)`
  4. Generate summary via LLM (use first ~3000 chars of full content before chunking)
  5. Parallel embedding generation: `asyncio.gather()` for summary + all chunks
  6. Save summary as chunk_order=0, is_summary=True
  7. Save text chunks starting from chunk_order=1
  8. Each chunk deduplicated by content_hash in repository.add()
- ✅ Tests: 2/2 passing

**Phase 3 Test Summary:**
- Total: 35/35 tests passing
- url_fetcher.py: 20 tests
- content_chunker.py: 13 tests
- url_processor.py: 2 tests

### Phase 4: Unified Random Endpoint & Response Builders - ✅ COMPLETE

**4.1 Create `src/random_selector.py`:** ✅ COMPLETE
- ✅ Function: `select_random_content(note_repo, chunk_repo) -> RandomSelection`
- ✅ Get counts from both repositories using `count_with_embeddings()`
- ✅ Weighted random selection based on counts (proportional to available content)
- ✅ Return either note or URL chunk
- Tests: Comprehensive test coverage with edge cases

**4.2 Add Unified Response Models & Response Builders:** ✅ COMPLETE
- ✅ Added to `src/repositories/models.py`:
  - `BookSource` and `URLSource` (discriminated union with `Literal` type field)
  - `NoteContent` and `URLChunkContent` (discriminated union with `Literal` type field)
  - `ContentWithRelatedItemsResponse` (unified response combining source + content + related items)
- ✅ Created `src/routers/response_builders.py` with:
  - `build_source_response_from_book()` - BookResponse → BookSource
  - `build_source_response_from_url()` - URLResponse → URLSource
  - `build_content_item_from_note()` - NoteRead → NoteContent
  - `build_content_item_from_chunk()` - URLChunkRead → URLChunkContent
  - `build_unified_response_for_note()- Combined note + book + related notes
  - `build_unified_response_for_chunk()` - Combined chunk + URL + related chunks
- Tests: 22 comprehensive tests in `src/routers/test_response_builders.py`

**4.3 Update `src/context_generation/additional_context.py`:** ✅ COMPLETE (with architectural improvement)
- ✅ Core function: `async get_additional_context_stream(llm_client, prompt, system_instruction)`
- ✅ Refactored: **Removed wrapper function** `get_additional_context_stream_for_chunk()`
- **Rationale:** Better separation of concerns - prompt creation happens at call site, not in this module
- **Implementation:** Callers use `create_chunk_context_prompt()` to create prompt, then pass to `get_additional_context_stream()`
- This approach keeps additional_context.py focused on generic streaming functionality
- Tests: 1 core test remaining in `src/context_generation/test_additional_context.py`

**4.4 Create `src/routers/notes.py` `/random/v2` endpoint:** ✅ COMPLETE
- ✅ Created new `/random/v2` endpoint with unified schema
- ✅ Notes only (URL chunk support to be added after migration)
- ✅ Uses `build_unified_response_for_note()` builder
- ✅ Same SSE streaming pattern (metadata → context_chunk → context_complete)
- ✅ Background evaluation for notes maintained
- ✅ Backwards compatible - existing `/random` unchanged
- Future: Add URL chunk branching after Phase 5 (migration + endpoints)

### Phase 5: URL-Specific Endpoints - ⚠️ PARTIALLY COMPLETE (3/4 endpoints)

**5.1 Create `src/routers/urls.py`:** ⚠️ PARTIALLY COMPLETE (4/4 endpoints - 3 implemented)

**Implemented Endpoints:**
- ✅ `POST /urls` - Ingest URL content (**synchronous**, blocks until complete)
  - Request: `{"url": "https://..."}`
  - Response: URL metadata + all chunks
  - **Enforces max content size limit** (rejects if exceeds settings.max_url_content_size)
  - **Returns existing URL if already ingested** (deduplication by URL)
  - Calls `process_url_content()` which handles fetch → chunk → summarize → embed
  - Error handling: 422 for fetch errors, 500 for unexpected errors

- ✅ `GET /urls` - List all URLs with chunk counts
  - Returns all processed URLs with metadata and chunk counts
  - Includes: id, url, title, fetched_at, created_at, chunk_count

- ✅ `GET /urls/{url_id}` - Get URL with metadata AND all chunks
  - Returns URL details (id, url, title, fetched_at, created_at)
  - Includes all chunks ordered by chunk_order (content, chunk_order, is_summary)
  - No AI context generation (lightweight endpoint for browsing)
  - Returns 404 if URL not found
  - Pattern: Similar to existing `/books/{id}` endpoint

**Not Yet Implemented Endpoints (Option A - Minimal):**
- ❌ `GET /urls/{url_id}/chunks/{chunk_id}` - SSE streaming endpoint for specific chunk
  - Same SSE events: metadata, context_chunk, context_complete
  - Generates AI context for the selected chunk
  - **No background evaluation** (per confirmed decision)
  - Pattern: mirror `/books/{book_id}/notes/{note_id}`

**Design Decision - Option A Rationale:**
- Simplified API surface (2 endpoints + 2 detail endpoints)
- `GET /urls/{url_id}` provides both metadata and chunks in one call (efficient for UI)
- Removes redundant `/urls/{url_id}/chunks` endpoint
- Users can browse all chunks, then drill into specific chunks with SSE for AI context

**5.2 Register router in `src/main.py`:** ✅ COMPLETE
- ✅ Router imported: `from src.routers import urls` (line 3)
- ✅ Router registered: `app.include_router(urls.router)` (line 89)
- ✅ OpenAPI tag added for documentation (lines 72-74)

### Phase 6: Search Integration - ❌ NOT STARTED

**6.1 Update `src/routers/search.py`:** ❌ NOT STARTED
- Search both notes and URL chunks in parallel using `asyncio.gather()`
- Combine results (allocate limit/2 to each source)
- Keep existing `SearchResult` model structure
- Group URL chunks by URL (similar to how notes are grouped by book)
- Note: May need to extend SearchResult or create separate search endpoint for URLs

**Implementation approach:**
```python
# Search both in parallel
similar_notes = note_repository.search_notes_by_embedding(embedding, limit=limit//2)
similar_chunks = chunk_repository.search_chunks_by_embedding(embedding, limit=limit//2)

# Group notes by book (existing logic)
# Group chunks by URL (new logic - similar pattern)
# Combine into response
```

### Phase 7: Dependency Injection & Configuration - ✅ COMPLETE

**7.1 Update `src/dependencies.py`:** ✅ COMPLETE
- ✅ Add: `get_url_repository()`, `get_urlchunk_repository()`
- Both functions follow existing patterns (depend on session, return interface)

**7.2 Update `src/config.py`:** ✅ COMPLETE
- ✅ Add setting: `max_url_content_size: int = 500_000  # 500KB HTML limit`
- ✅ All URL-related settings configured

**7.3 Update `src/test_utils.py`:** ✅ COMPLETE
- ✅ Add: `StubURLRepository` with full interface implementation
- ✅ Add: `StubURLChunkRepository` with full interface implementation
- Includes deduplication logic and stub methods for all repository operations

### Phase 8: Testing - ⚠️ MOSTLY COMPLETE

**8.1 Unit Tests:** ✅ COMPLETE
- ✅ `src/url_ingestion/test_url_fetcher.py` - URL fetching, parsing, error handling (20 tests)
- ✅ `src/url_ingestion/test_content_chunker.py` - Chunking logic, edge cases (13 tests)
- ✅ `src/url_ingestion/test_url_processor.py` - Processing pipeline (2 tests)
- ✅ `src/routers/test_random_selector.py` - Random selection logic with edge cases

**8.2 Repository Tests:** ✅ COMPLETE
- ✅ `src/url_ingestion/repositories/test_url_repository.py` - URL CRUD & deduplication
- ✅ `src/url_ingestion/repositories/test_urlchunk_repository.py` - URLChunk CRUD, vector search, random selection

**8.3 Router Tests:** ✅ COMPLETE (test_urls.py)
- ✅ `src/routers/test_response_builders.py` - Unified response builder tests (22 tests)
- ✅ `src/routers/test_urls.py` - Test URL endpoints (6 tests, no patching via dependency injection)
  - ✅ `test_ingest_url_fetch_error` - Error handling (422 unprocessable entity)
  - ✅ `test_ingest_url_success` - Successful ingestion with chunk validation
  - ✅ `test_get_urls_empty` - Empty URL list endpoint
  - ✅ `test_get_urls_with_urls` - URL listing with chunk counts
  - ✅ `test_ingest_url_invalid_request` - Invalid request validation
  - ✅ `test_ingest_url_invalid_format` - URL format validation
- ❌ Update `src/routers/test_streaming.py` - Test unified /random (blocked on Phase 4.4 implementation)

**8.4 Testing Commands:**
```bash
uv run ruff format  # Format code
uv run pytest -v    # Run all tests
uv run pyright      # Type checking
```

### Phase 9: Documentation - ❌ NOT STARTED

**9.1 Update `CLAUDE.md`:** ❌ NOT STARTED
- Add URL endpoints to API Endpoints section
- Add URL processing files to Key Files section
- Update development workflow if needed

---

## Implementation Order

1. ✅ **Phase 1** (Models & Migration) - COMPLETE (models + migration with fixed HNSW index)
2. ✅ **Phase 2** (Repositories) - Data access layer COMPLETE
3. ✅ **Phase 3** (Processing) - URL fetching, chunking, processing COMPLETE (35/35 tests passing)
4. ✅ **Phase 4** (Unified /random) - All components COMPLETE including /random/v2 endpoint
5. ⚠️ **Phase 5** (URL Endpoints) - PARTIALLY COMPLETE (3 of 4 endpoints: POST /urls, GET /urls, GET /urls/{url_id})
6. ❌ **Phase 6** (Search) - Enhanced search NOT STARTED
7. ✅ **Phase 7** (DI & Config) - Wire everything together COMPLETE
8. ⚠️ **Phase 8** (Testing) - Unit & repo tests COMPLETE, router tests for /urls COMPLETE (9 tests)
9. ❌ **Phase 9** (Documentation) - Update docs NOT STARTED

**Remaining Phase 5 Work (Option A - 1 endpoint):**
- ❌ `GET /urls/{url_id}/chunks/{chunk_id}` - SSE streaming for specific chunk with AI context

**Next Steps:**
1. Complete Phase 5 by implementing the final endpoint (GET /urls/{url_id}/chunks/{chunk_id})
2. Add tests for SSE streaming endpoint
3. Proceed with Phase 6 (Search integration with URL chunks)
4. Phase 9 (Documentation updates)

**Key Pattern to Follow:** Mirror existing Book/Note architecture everywhere:
- Models: Book → URL, Note → URLChunk
- Processing: `notebook_processor.py` → `url_processor.py`
- Repositories: `BookRepository` → `URLRepository`, `NoteRepository` → `URLChunkRepository`
- Testing: Follow existing test patterns

---

## Critical Files Reference

**Models & Schema:**
- `src/repositories/models.py` - Add URL/URLChunk models + unified response models

**New Processing Files:**
- `src/url_fetcher.py` - Fetch URL content (httpx + BeautifulSoup)
- `src/content_chunker.py` - Chunk text by paragraphs
- `src/url_processor.py` - Full processing pipeline (fetch → chunk → summarize → embed)
- `src/random_selector.py` - Application-level random selection

**New Repository Files:**
- `src/repositories/url_repository.py` - URL CRUD operations
- `src/repositories/urlchunk_repository.py` - URLChunk CRUD + vector search

**Modified Core Files:**
- `src/routers/notes.py` - Update `/random` to unified version (CRITICAL)
- `src/routers/response_builders.py` - Add unified response builders
- `src/additional_context.py` - Add context generation for URL chunks
- `src/dependencies.py` - Add URL repository dependencies

**New Router:**
- `src/routers/urls.py` - All URL-specific endpoints

**Optional Updates:**
- `src/routers/search.py` - Include URL chunks in search
- `src/config.py` - Add URL-related settings

---

## Implementation Notes & Clarifications

### Repository Count Methods
Add `count_with_embeddings()` to both existing and new repositories:
- Returns SQL COUNT of rows where embedding IS NOT NULL
- More efficient than `len(list_all())` for random selection
- Pattern: `SELECT COUNT(*) FROM table WHERE embedding IS NOT NULL`

### Vector Index Type
Use HNSW (Hierarchical Navigable Small World) for consistency with existing Note table:
- Migration should create HNSW index, not IVFFlat
- Optimal for datasets < 1M vectors
- Matches existing Note.embedding index

### Deduplication Strategy
- **URLs**: Deduplicate by `url` field (unique constraint)
- **URLChunks**: Deduplicate by `content_hash` (SHA-256, unique constraint)
- Both handled in repository `add()` methods (check before insert, return existing if found)

### Dependencies to Add
- `httpx` - Async HTTP client for URL fetching
- `beautifulsoup4` - HTML parsing
- Already have: `pgvector`, `openai`, `sqlmodel`, `fastapi`

### Processing Flow Summary
1. **POST /urls** receives URL
2. Check if URL exists in database → return existing if found
3. Fetch URL content with httpx (enforce 500KB limit)
4. Parse HTML with BeautifulSoup, extract text and title
5. Chunk text by paragraphs (max 1000 tokens/~4000 chars)
6. Generate LLM summary from first ~3000 chars
7. Generate embeddings in parallel for summary + all chunks
8. Save to database (summary as chunk_order=0, is_summary=True)
9. Return complete URL record with all chunks
10. **No background evaluation** (only for Kindle notes)

---

## Progress Summary

**COMPLETED (Phase 1-4):**
- ✅ URL and URLChunk models (commit b060b83)
- ✅ Repository interfaces with count_with_embeddings (commit 4f3df43)
- ✅ URL and URLChunk repository implementations (commit 02b37bc)
- ✅ URL fetcher module with full HTTP/HTML handling (20/20 tests) - `src/url_ingestion/url_fetcher.py`
- ✅ Content chunker module with paragraph-based splitting (13/13 tests) - `src/url_ingestion/content_chunker.py`
- ✅ URL processor module with complete pipeline (2/2 tests) - `src/url_ingestion/url_processor.py`
- ✅ Random selector function with weighted selection - `src/routers/random_selector.py`
- ✅ Unified response models (BookSource, URLSource, NoteContent, URLChunkContent, ContentWithRelatedItemsResponse) - `src/repositories/models.py`
- ✅ Response builder functions (6 functions, 22 comprehensive tests) - `src/routers/response_builders.py`
- ✅ Additional context streaming (refactored to remove wrapper, keep generic function) - `src/context_generation/additional_context.py`
- ✅ **NEW: `/random/v2` endpoint with unified schema** (commit 0c716c5) - `src/routers/notes.py`

**Test Status:** 176 tests passing across all modules
- Phase 1-3: 35 tests (URL processing pipeline)
- Phase 4: 22 tests (response builders) + 1 test (context streaming)
- Phase 5: 9 tests (URL endpoints) ✅ UPDATED (added 3 tests for GET /urls/{url_id})
- Phase 7: Repositories fully tested
- Total: 67+ URL-feature tests + existing 109 tests

**COMPLETED IN PREVIOUS SESSION:**
1. ✅ Phase 5.1 - POST /urls endpoint (ingest URL content)
   - Synchronous processing: fetches, chunks, summarizes, embeds in one call
   - Deduplication by URL (returns existing if already ingested)
   - Error handling: 422 for fetch errors, 500 for unexpected errors
   - Size limit enforcement via `settings.max_url_content_size`

2. ✅ Phase 5.1 - GET /urls endpoint (list all URLs)
   - Returns all ingested URLs with chunk counts
   - Includes metadata: id, url, title, fetched_at, created_at

3. ✅ Phase 8.3 - URL Endpoint Testing (test_urls.py)
   - Created `StubURLFetcher` class for testing without external HTTP calls
   - Implemented dependency injection for URL fetcher via `get_url_fetcher()` factory
   - Refactored test fixture `setup_url_deps()` with clean API
   - **Eliminated patching** - tests use pure dependency injection instead of mocks
   - Added comprehensive test coverage (6 tests):
     - Error handling (422 for fetch failures)
     - Successful ingestion with chunk validation
     - URL listing endpoints
     - Input validation (missing/invalid URLs)
   - Tests validate observable outcomes (repository state) not implementation details
   - All tests passing, zero lint/type errors

4. ✅ Phase 5.2 - Router registration
   - Router imported and registered in `src/main.py`
   - OpenAPI documentation tags added

**COMPLETED IN THIS SESSION:**
1. ✅ Phase 5.1 - GET /urls/{url_id} endpoint (get URL with chunks)
   - Returns URL metadata + all chunks ordered by chunk_order
   - No AI context generation (lightweight for browsing)
   - Returns 404 if URL not found
   - Follows same pattern as existing Book/Note architecture

2. ✅ Tests for GET /urls/{url_id} (3 tests added)
   - test_get_url_with_chunks_not_found - 404 error handling
   - test_get_url_with_chunks_empty - URL with no chunks
   - test_get_url_with_chunks_success - Chunks ordered by chunk_order

3. ✅ Repository fixes
   - Fixed URLChunkRepository.get_by_url_id() ordering (SQLAlchemy syntax)
   - Fixed StubURLChunkRepository to sort chunks by chunk_order
   - All 9 tests passing, type checking clean

**REMAINING PHASE 5 WORK (Option A - 1 final endpoint):**
- ❌ `GET /urls/{url_id}/chunks/{chunk_id}` - SSE streaming endpoint for specific chunk
  - Should follow same pattern as `/books/{book_id}/notes/{note_id}`
  - Same SSE events: metadata, context_chunk, context_complete
  - No background evaluation (per design decision)

**DESIGN CHOICE APPLIED - Option A:**
- Removed redundant `/urls/{url_id}/chunks` endpoint
- Implemented 3 of 4 endpoints (POST /urls, GET /urls, GET /urls/{url_id})
- `GET /urls/{url_id}` returns both metadata AND chunks in one call for efficiency

**NEXT STEPS:**
- Complete Phase 5 with final endpoint: GET /urls/{url_id}/chunks/{chunk_id} (SSE streaming)
- Add tests for SSE streaming endpoint
- Phase 6 - Search integration (include URL chunks in semantic search)
- Phase 9 - Documentation updates

---

*Plan Status: **PHASE 5 PARTIAL - 3/4 ENDPOINTS COMPLETE** (Phases 1-4 complete, Phase 5 partial - 3/4 endpoints done, 1 remaining, Phase 6-9 pending)*

*Last Updated: 2026-01-01 - Implemented GET /urls/{url_id} endpoint (commit 9222ef8). Returns URL metadata + all chunks ordered by chunk_order. All tests passing (9/9). Only final SSE streaming endpoint remains for Phase 5.*
