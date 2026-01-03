# URL Content Ingestion Feature - Implementation Plan

## Overview

✅ **COMPLETE** - Successfully added capability to ingest content from URLs, chunk it for searchability, generate summaries, and serve it through the existing API infrastructure alongside Kindle notes.

**Status: Production-Ready**
- All infrastructure implemented and tested
- Seamlessly integrated with existing Kindle notes system
- 179 tests passing, 0 type errors
- Full documentation complete

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

### Phase 5: URL-Specific Endpoints - ✅ COMPLETE (4/4 endpoints)

**5.1 Create `src/routers/urls.py`:** ✅ COMPLETE (4/4 endpoints - all implemented)

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

- ✅ `GET /urls/{url_id}/chunks/{chunk_id}` - SSE streaming endpoint for specific chunk
  - Streams URL chunk with AI-generated context via Server-Sent Events
  - Same SSE events: metadata, context_chunk, context_complete, error
  - Returns chunk metadata + related chunks from same URL (limit: 3)
  - Uses unified response schema (ContentWithRelatedItemsResponse)
  - **No background evaluation** (per confirmed decision - evaluations only for Kindle notes)
  - Pattern: mirrors `/books/{book_id}/notes/{note_id}`
  - Tests: 3 comprehensive tests (404 errors + happy path SSE streaming)
  - Commit: c9f900a

**Design Decision - Option A Rationale:**
- Simplified API surface (2 endpoints + 2 detail endpoints)
- `GET /urls/{url_id}` provides both metadata and chunks in one call (efficient for UI)
- Removes redundant `/urls/{url_id}/chunks` endpoint
- Users can browse all chunks, then drill into specific chunks with SSE for AI context

**5.2 Register router in `src/main.py`:** ✅ COMPLETE
- ✅ Router imported: `from src.routers import urls` (line 3)
- ✅ Router registered: `app.include_router(urls.router)` (line 89)
- ✅ OpenAPI tag added for documentation (lines 72-74)

### Phase 6: Search Integration - ✅ COMPLETE

**6.1 Update `src/routers/search.py`:** ✅ MERGED TO MASTER
- ✅ Search both notes and URL chunks in parallel using `asyncio.gather()`
- ✅ Combine results (allocate limit/2 to each source)
- ✅ Extended `SearchResult` model to support both books and urls arrays
- ✅ Group URL chunks by URL (similar to how notes are grouped by book)
- ✅ Added `get_by_ids()` method to URLRepository for efficient batch lookups
- ✅ Fixed database session concurrency issue in /search endpoint (Commit 8bda463)

**Implementation Status:**
- ✅ Commit: `5ae31c2` - "Phase 6: integrate URL chunks into semantic search endpoint"
- ✅ Merged: Now integrated into master branch
- ✅ Tests: All search tests passing with mixed results validation
- ✅ Production: Ready for use - Phase 6 feature complete and stable

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

### Phase 8: Testing - ✅ COMPLETE

**8.1 Unit Tests:** ✅ COMPLETE
- ✅ `src/url_ingestion/test_url_fetcher.py` - URL fetching, parsing, error handling (20 tests)
- ✅ `src/url_ingestion/test_content_chunker.py` - Chunking logic, edge cases (13 tests)
- ✅ `src/url_ingestion/test_url_processor.py` - Processing pipeline (2 tests)
- ✅ `src/routers/test_random_selector.py` - Random selection logic with edge cases
- ✅ `src/routers/test_random_content.py` - Unified /random/v2 endpoint with URL chunk support (4 focused tests after cleanup)

**8.2 Repository Tests:** ✅ COMPLETE
- ✅ `src/url_ingestion/repositories/test_url_repository.py` - URL CRUD & deduplication
- ✅ `src/url_ingestion/repositories/test_urlchunk_repository.py` - URLChunk CRUD, vector search, random selection (13 tests)

**8.3 Router Tests:** ✅ COMPLETE (test_urls.py + test_search.py merged to master)
- ✅ `src/routers/test_response_builders.py` - Unified response builder tests (22 tests)
- ✅ `src/routers/test_urls.py` - Test URL endpoints (11 tests, no patching via dependency injection)
  - ✅ `test_ingest_url_fetch_error` - Error handling (422 unprocessable entity)
  - ✅ `test_ingest_url_success` - Successful ingestion with chunk validation
  - ✅ `test_get_urls_empty` - Empty URL list endpoint
  - ✅ `test_get_urls_with_urls` - URL listing with chunk counts
  - ✅ `test_ingest_url_invalid_request` - Invalid request validation
  - ✅ `test_ingest_url_invalid_format` - URL format validation
  - ✅ `test_get_url_with_chunks_not_found` - 404 when URL doesn't exist
  - ✅ `test_get_url_with_chunks_empty` - URL with no chunks
  - ✅ `test_get_url_with_chunks_success` - Chunks ordered by chunk_order
  - ✅ `test_get_chunk_with_context_stream_not_found` - SSE 404 chunk not found
  - ✅ `test_get_chunk_with_context_stream_success` - SSE happy path with event streaming
- ✅ `src/routers/test_search.py` - Updated for mixed notes + URL chunks search (merged to master)

**8.4 Testing Commands:**
```bash
uv run ruff format  # Format code
uv run pytest -v    # Run all tests
uv run pyright      # Type checking
```

**Test Summary (Master Branch):**
- **Total Tests:** 179 passing
- **Type Errors:** 0
- **Coverage:** All phases 1-8 with comprehensive test coverage

### Phase 9: Documentation - ✅ COMPLETE

**9.1 Update `CLAUDE.md`:** ✅ COMPLETE
- ✅ Updated API Endpoints section with all URL endpoints
- ✅ Updated Key Files section with URL processing and router files
- ✅ Added unified response models documentation
- ✅ Added search integration with URL chunks
- ✅ Updated testing patterns section with fixture documentation
- ✅ Added API testing guidance with /api-test skill
- ✅ Commit: `1a1218e` - "docs: update plan and CLAUDE.md to reflect current state"

---

## Implementation Order

1. ✅ **Phase 1** (Models & Migration) - COMPLETE (models + migration with fixed HNSW index)
2. ✅ **Phase 2** (Repositories) - Data access layer COMPLETE
3. ✅ **Phase 3** (Processing) - URL fetching, chunking, processing COMPLETE (35/35 tests passing)
4. ✅ **Phase 4** (Unified /random) - COMPLETE with Phase 4.4 URL chunk support (Commit 25c0866)
5. ✅ **Phase 5** (URL Endpoints) - COMPLETE (all 4 endpoints: POST /urls, GET /urls, GET /urls/{url_id}, GET /urls/{url_id}/chunks/{chunk_id})
6. ✅ **Phase 6** (Search) - COMPLETE and merged to master (Commit 5ae31c2, fixed in 8bda463)
7. ✅ **Phase 7** (DI & Config) - Wire everything together COMPLETE
8. ✅ **Phase 8** (Testing) - ALL TESTS COMPLETE (179 tests passing, 0 type errors)
9. ✅ **Phase 9** (Documentation) - COMPLETE (CLAUDE.md updated with full URL feature documentation)

**Phase 4.4 Complete (Commit 25c0866):**
- ✅ Added URL chunk support to `/random/v2` endpoint
- ✅ Unified random selection between Kindle notes and URL chunks
- ✅ Weighted random distribution (proportional to content count)
- ✅ Separate evaluation logic (notes only, not URL chunks)
- ✅ Tests refactored and simplified to 4 focused tests

**Phase 6 Complete (Commit 5ae31c2, fixed in 8bda463):**
- ✅ Extended `/search` endpoint to support both notes and URL chunks
- ✅ Modified SearchResult model to include both books and urls
- ✅ Parallel search with equal allocation (50% notes, 50% chunks)
- ✅ Comprehensive tests with mixed result validation
- ✅ Fixed database session concurrency issue in /search endpoint
- ✅ **Status:** Merged to master, production-ready

**Next Steps:**
- ✅ All phases complete - Feature fully implemented and documented
- Ongoing: Monitor performance and gather user feedback

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

**COMPLETED PHASES 1-5 (Master Branch):**
- ✅ Phase 1: URL and URLChunk models with HNSW vector indexes
- ✅ Phase 2: URL and URLChunk repository implementations with deduplication
- ✅ Phase 3: URL fetching, chunking, and processing pipeline (35 tests)
- ✅ Phase 4: Unified /random/v2 endpoint with URL chunk support (Phase 4.4 - Commit 25c0866)
- ✅ Phase 5: Complete URL endpoints (POST /urls, GET /urls, GET /urls/{url_id}, GET /urls/{url_id}/chunks/{chunk_id})
- ✅ Phase 7: Dependency injection and configuration
- ✅ Phase 8: Comprehensive test coverage (178 tests passing)

**COMPLETED ALL PHASES (Master Branch):**
- ✅ Phase 1-5: Core URL infrastructure (endpoints, processing, repositories)
- ✅ Phase 6: Search integration with URL chunks (merged to master)
- ✅ Phase 7: Dependency injection and configuration
- ✅ Phase 8: Comprehensive test coverage (179 tests)
- ✅ Phase 9: Full documentation updated

**KEY ACHIEVEMENTS:**

1. **URL Infrastructure Complete** - All 4 endpoints working with full SSE streaming support
2. **Unified Content Selection** - /random/v2 seamlessly selects between Kindle notes and URL chunks
3. **Semantic Search Unified** - /search returns both book highlights and URL chunks in single query
4. **Test Coverage Comprehensive** - 179 tests passing across all phases
5. **Type Safety** - 0 type errors with full pyright checking
6. **Clean Architecture** - Mirrors existing Book/Note patterns throughout
7. **Documentation Complete** - CLAUDE.md updated with full feature coverage

**CURRENT CODEBASE STATE:**

- **Master Branch (Current - Production Ready):**
  - All Phases 1-9 complete and merged
  - Latest commit: 8bda463 - Database session fix for /search endpoint
  - 179 tests passing, 0 type errors
  - Full API documentation in docstrings and CLAUDE.md
  - **Status: Production-ready - all features complete and tested**

**FEATURE COMPLETENESS:**
- ✅ URL content ingestion (fetch, parse, chunk, summarize, embed)
- ✅ Unified random content selection (notes vs chunks)
- ✅ Unified semantic search (both content types)
- ✅ SSE streaming for all content types
- ✅ Background evaluation for Kindle notes only
- ✅ Deduplication at all levels (URLs, chunks, notes)
- ✅ Comprehensive test coverage (179 tests, 0 errors)

---

*Plan Status: **ALL PHASES 1-9 COMPLETE** (Master Branch)*

*Current Branch: master*

*Latest Commit: 8bda463 - Fix database session concurrency issue in /search endpoint*

*Last Updated: 2026-01-03 - All phases complete: URL feature fully implemented, integrated, tested (179 tests), documented, and production-ready. Phase 6 merged to master. CLAUDE.md updated.*
