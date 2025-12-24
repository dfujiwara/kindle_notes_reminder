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

### Phase 1: Database Models & Migration (Foundation) - ⚠️ PARTIALLY COMPLETE

**1.1 Add Models to `src/repositories/models.py`:** ⚠️ PARTIALLY COMPLETE
- ✅ `URL` model: `id, url (unique), title, fetched_at, created_at` (commit b060b83)
- ✅ `URLChunk` model: `id, content, content_hash (unique), url_id (FK), chunk_order, is_summary, embedding (Vector 1536), created_at` (commit b060b83)
- ❌ **TODO:** Unified response models: `SourceResponse`, `ContentItemResponse`, `ContentWithRelatedItemsResponse`
- Pattern: Follow existing Book/Note model structure (Base → Create → Table → Read/Response)

**1.2 Create Migration:** ❌ NOT STARTED
```bash
uv run alembic revision --autogenerate -m "add url and urlchunk tables"
```
- Add unique constraint on `url.url` and `urlchunk.content_hash`
- Add indexes: `url_id`, `chunk_order`, HNSW vector index on `embedding`
- Apply: `uv run alembic upgrade head`

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

### Phase 3: URL Fetching & Content Processing - ❌ NOT STARTED

**3.1 Create `src/url_fetcher.py`:** ❌ NOT STARTED
- Function: `async fetch_url_content(url: str) -> FetchedContent`
- Use `httpx.AsyncClient` for HTTP requests (timeout: 30s, follow redirects)
- Use `BeautifulSoup` to parse HTML and extract text
- Remove script/style/nav/footer/header tags
- Clean excessive whitespace
- Extract title from `<title>` tag
- Raise `URLFetchError` on failures

**3.2 Create `src/content_chunker.py`:** ❌ NOT STARTED
- Function: `chunk_text_by_paragraphs(text: str, max_chunk_size: int = 1000) -> list[TextChunk]`
- Split by double newlines (paragraphs)
- Combine small paragraphs up to max size
- Split large paragraphs if they exceed max size
- Return chunks with content, SHA-256 hash, and order

**3.3 Create `src/url_processor.py`:** ❌ NOT STARTED
- Pattern: Mirror `notebook_processor.py` structure
- Function: `async process_url_content(...) -> URLWithChunksResponse`
- **Processing:** Synchronous (blocks until complete)
- Steps:
  1. **Check if URL exists** → return existing URL with chunks if found (no re-fetching)
  2. Fetch URL content with `fetch_url_content()` (enforces size limit)
  3. Chunk content using `chunk_text_by_paragraphs(max_chunk_size=1000)`
  4. Generate summary via LLM (use first ~3000 chars of full content before chunking)
  5. Parallel embedding generation: `asyncio.gather()` for summary + all chunks
  6. Save summary as chunk_order=0, is_summary=True
  7. Save text chunks starting from chunk_order=1
  8. Each chunk deduplicated by content_hash in repository.add()

**Summary Generation Detail:**
- Truncate full content to ~3000 chars for LLM input
- Generate 2-3 sentence summary using LLM
- Store summary as special URLChunk (is_summary=True, chunk_order=0)
- Summary gets its own embedding for URL-level discovery

### Phase 4: Unified Random Endpoint - ❌ NOT STARTED

**4.1 Create `src/random_selector.py`:** ❌ NOT STARTED
- Function: `select_random_content(note_repo, chunk_repo) -> RandomSelection`
- Get counts from both repositories using `count_with_embeddings()`
- Weighted random selection based on counts (proportional to available content)
- Return either note or URL chunk
- Implementation:
  ```python
  note_count = note_repo.count_with_embeddings()
  chunk_count = chunk_repo.count_with_embeddings()
  total = note_count + chunk_count

  rand = random.randint(0, total - 1)
  if rand < note_count:
      return RandomSelection(content_type="note", note=note_repo.get_random())
  else:
      return RandomSelection(content_type="url_chunk", url_chunk=chunk_repo.get_random())
  ```

**4.2 Update `src/routers/response_builders.py`:** ❌ NOT STARTED
- Add: `build_source_response_from_book()`, `build_source_response_from_url()`
- Add: `build_content_item_from_note()`, `build_content_item_from_chunk()`
- Add: `build_unified_response_for_note()`, `build_unified_response_for_chunk()`

**4.3 Update `src/additional_context.py`:** ❌ NOT STARTED
- Add: `async get_additional_context_stream_for_chunk()` (similar to existing note function)
- Use URL-specific prompt format

**4.4 Rewrite `src/routers/notes.py` `/random` endpoint:** ❌ NOT STARTED
- Use `select_random_content()` to pick note or URL chunk
- Branch based on content type
- Build unified response using new response builders
- Stream via SSE (same event types: metadata, context_chunk, context_complete)
- **Background evaluation for notes ONLY** (skip for URL chunks per confirmed decision)

### Phase 5: URL-Specific Endpoints - ❌ NOT STARTED

**5.1 Create `src/routers/urls.py`:** ❌ NOT STARTED
- `POST /urls` - Ingest URL content (**synchronous**, blocks until complete)
  - Request: `{"url": "https://..."}`
  - Response: URL metadata + all chunks
  - **Enforces max content size limit** (rejects if exceeds settings.max_url_content_size)
  - **Returns existing URL if already ingested** (deduplication by URL)
  - Calls `process_url_content()` which handles fetch → chunk → summarize → embed
- `GET /urls` - List URLs with chunk counts
- `GET /urls/{url_id}` - Get URL metadata
- `GET /urls/{url_id}/chunks` - Get all chunks for URL (ordered by chunk_order)
- `GET /urls/{url_id}/chunks/{chunk_id}` - SSE streaming endpoint (pattern: mirror `/books/{id}/notes/{id}`)
  - Same SSE events: metadata, context_chunk, context_complete
  - **No background evaluation** (per confirmed decision)

**5.2 Register router in `src/main.py`:** ❌ NOT STARTED
```python
from src.routers import urls
app.include_router(urls.router)
```

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

### Phase 7: Dependency Injection & Configuration - ❌ NOT STARTED

**7.1 Update `src/dependencies.py`:** ❌ NOT STARTED
- Add: `get_url_repository()`, `get_urlchunk_repository()`

**7.2 Update `src/config.py`:** ❌ NOT STARTED
- Add setting: `max_url_content_size: int = 500_000  # 500KB HTML limit`
- Optional settings: `url_fetch_timeout`, `max_chunk_size`

**7.3 Update `src/test_utils.py`:** ❌ NOT STARTED
- Add: `StubURLRepository`, `StubURLChunkRepository`

### Phase 8: Testing - ❌ NOT STARTED

**8.1 Unit Tests (create new files):** ❌ NOT STARTED
- `src/test_url_fetcher.py` - Test fetching, parsing, error handling
- `src/test_content_chunker.py` - Test chunking logic, edge cases
- `src/test_url_processor.py` - Test processing pipeline
- `src/test_random_selector.py` - Test random selection logic

**8.2 Repository Tests:** ❌ NOT STARTED
- `src/repositories/test_url_repository.py` - Pattern: mirror `test_book_repository.py`
- `src/repositories/test_urlchunk_repository.py` - Pattern: mirror `test_note_repository.py`

**8.3 Router Tests:** ❌ NOT STARTED
- `src/routers/test_urls.py` - Test all URL endpoints
- `src/routers/test_url_streaming.py` - Pattern: mirror `test_streaming.py`
- Update `src/routers/test_streaming.py` - Test unified /random

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

1. ⚠️ **Phase 1** (Models & Migration) - Partially complete, need unified response models + migration
2. ✅ **Phase 2** (Repositories) - Data access layer COMPLETE
3. ❌ **Phase 3** (Processing) - URL fetching, chunking, processing NOT STARTED
4. ❌ **Phase 4** (Unified /random) - Update existing endpoint NOT STARTED
5. ❌ **Phase 5** (URL Endpoints) - New API surface NOT STARTED
6. ❌ **Phase 6** (Search) - Enhanced search NOT STARTED
7. ❌ **Phase 7** (DI & Config) - Wire everything together NOT STARTED
8. ❌ **Phase 8** (Testing) - Ensure quality throughout NOT STARTED
9. ❌ **Phase 9** (Documentation) - Update docs NOT STARTED

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

**COMPLETED:**
- ✅ URL and URLChunk models (commit b060b83)
- ✅ Repository interfaces with count_with_embeddings (commit 4f3df43)
- ✅ URL and URLChunk repository implementations (commit 02b37bc)

**NEXT STEPS:**
1. Add unified response models (SourceResponse, ContentItemResponse, ContentWithRelatedItemsResponse)
2. Create and apply database migration
3. Begin Phase 3 (URL fetching & content processing)

---

*Plan Status: **IN PROGRESS** (Phase 1-2 complete, Phase 3+ remaining)*

*Last Updated: 2025-12-23 - Updated with completion status for Phases 1-2*
