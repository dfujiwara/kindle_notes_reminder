# Tweet Content Ingestion Feature - Implementation Plan

## Overview

Add capability to ingest tweets (and tweet threads) into the system, making them searchable alongside Kindle notes and URL content. Tweets will be stored with embeddings for semantic search and served through the existing API infrastructure.

**Status: Planning**

## Current Architecture Understanding

**Key Components (from URL ingestion):**

- **Data Models** (`src/repositories/models.py`):
  - URL (1:N) → URLChunk relationship
  - URLChunk: content, content_hash (SHA-256), embedding (1536D), url_id FK
  - Unique constraints and HNSW vector index on embeddings

- **API Patterns** (`src/routers/urls.py`):
  - SSE streaming endpoints with unified response schema
  - Event types: `metadata`, `context_chunk`, `context_complete`, `error`
  - Background tasks only for Kindle notes evaluation

- **Processing Pipeline** (`src/url_ingestion/`):
  - Fetch → Parse → Chunk → Summarize → Embed → Store
  - Parallel embedding generation with `asyncio.gather()`
  - Deduplication by URL and content_hash

## Design Decisions

### 1. Data Model: Tweet vs TweetThread Approach

**Decision:** Create `Tweet` and `TweetThread` models where a thread contains multiple tweets.

**Rationale:**
- Tweets are short (280 chars max) - individual tweets don't need chunking
- Thread conversations are the natural "document" unit (like a URL page)
- Each tweet in a thread can be embedded separately for fine-grained search
- Standalone tweets (non-thread) stored as single-tweet threads

**Models:**
```python
Tweet:
  - id, tweet_id (Twitter's ID, unique), author_username, author_display_name
  - content, media_urls (JSON list), thread_id (FK), position_in_thread
  - embedding (Vector 1536), tweeted_at, created_at

TweetThread:
  - id, root_tweet_id (unique), author_username, author_display_name
  - title (generated summary or first ~50 chars), tweet_count
  - fetched_at, created_at
```

### 2. Tweet Fetching Strategy

**Decision:** Support multiple input formats with Twitter API v2.

**Input formats:**
- Tweet URL: `https://twitter.com/user/status/123456789`
- Tweet URL (x.com): `https://x.com/user/status/123456789`
- Direct tweet ID: `123456789`

**Fetching approach:**
- Use Twitter API v2 with Bearer Token authentication
- Fetch conversation thread when ingesting a tweet (configurable depth)
- Extract: text, author info, media URLs, thread relationships
- Handle rate limiting with exponential backoff

### 3. Processing Model

**Decision:** Synchronous processing (same as URL ingestion).

**Rationale:**
- Simpler error handling
- Immediate user feedback
- Twitter API is fast for single tweets/threads
- Consistent with existing URL pattern

### 4. Duplicate Handling

**Decision:** Deduplicate by `root_tweet_id` for threads, `tweet_id` for individual tweets.

**Behavior:**
- If thread already exists, return existing record without re-fetching
- Individual tweets within threads deduplicated by `tweet_id`
- Option to force refresh with `?refresh=true` query parameter

### 5. Thread Depth Configuration

**Decision:** Configurable thread depth with sensible defaults.

**Settings:**
- `max_thread_depth: int = 50` - Maximum tweets to fetch in a thread
- `fetch_replies: bool = false` - Whether to include replies (not just thread continuation)

### 6. Summary Generation

**Decision:** Generate thread summary via LLM for multi-tweet threads.

**Implementation:**
- For threads with 2+ tweets: Generate LLM summary of entire thread
- For single tweets: Use tweet content directly (no summary needed)
- Summary stored in `TweetThread.title` field
- Summary also used for thread-level semantic search

### 7. Embedding Strategy

**Decision:** Embed each individual tweet AND thread summary.

**Rationale:**
- Fine-grained search: Find specific tweets within threads
- Thread-level search: Find threads by topic
- Consistent with URL chunk pattern

### 8. Unified Response Integration

**Decision:** Add `TweetSource` and `TweetContent` to unified response schema.

**Schema additions:**
```python
TweetSource:
  - id, title, type: Literal["tweet_thread"]
  - author_username, author_display_name
  - root_tweet_id, tweet_count
  - created_at

TweetContent:
  - id, content_type: Literal["tweet"]
  - content, author_username
  - position_in_thread, media_urls
  - tweeted_at, created_at
```

### 9. Random Selection Integration

**Decision:** Include tweets in `/random/v2` weighted selection.

**Implementation:**
- Add `Tweet.count_with_embeddings()` to random selection weights
- Proportional selection across notes, URL chunks, and tweets

### 10. Search Integration

**Decision:** Include tweets in `/search` endpoint.

**Implementation:**
- Search tweets alongside notes and URL chunks
- Allocate 1/3 of limit to each content type (adjustable)
- Group tweets by thread in results

---

## API Endpoints

### Tweet-Specific Endpoints

- `POST /tweets` - Ingest tweet or thread
  - Request: `{"tweet_url": "https://twitter.com/..."} or {"tweet_id": "123..."}`
  - Optional: `thread_depth`, `include_replies`
  - Response: Thread metadata + all tweets

- `GET /tweets` - List all ingested threads with tweet counts

- `GET /tweets/{thread_id}` - Get thread with all tweets (sorted by position)

- `GET /tweets/{thread_id}/tweets/{tweet_id}` - Specific tweet with AI context (SSE stream)

### Updated Existing Endpoints

- `GET /random/v2` - Now includes tweets in weighted random selection
- `GET /search` - Now includes tweets in semantic search results

---

## Implementation Plan

### Phase 1: Database Models & Migration (Foundation)

**1.1 Add Models to `src/repositories/models.py`:**
- [ ] `TweetThread` model: `id, root_tweet_id (unique), author_username, author_display_name, title, tweet_count, fetched_at, created_at`
- [ ] `Tweet` model: `id, tweet_id (unique), author_username, author_display_name, content, media_urls (JSON), thread_id (FK), position_in_thread, embedding (Vector 1536), tweeted_at, created_at`
- [ ] Unified response models:
  - `TweetThreadSource` (with `type: Literal["tweet_thread"]`)
  - `TweetContent` (with `content_type: Literal["tweet"]`)

**1.2 Create Migration:**
- [ ] Generate migration: `uv run alembic revision --autogenerate -m "add tweet tables"`
- [ ] Add HNSW index on Tweet.embedding (raw SQL for operator class)
- [ ] Add unique constraints: root_tweet_id, tweet_id
- [ ] Add foreign key: tweet.thread_id → tweet_thread.id

**1.3 Add Repository Interfaces:**
- [ ] Create `src/tweet_ingestion/repositories/interfaces.py`
- [ ] `TweetThreadRepositoryInterface`: add, get, get_by_root_tweet_id, list_threads, delete
- [ ] `TweetRepositoryInterface`: add, get, get_by_tweet_id, get_random, find_similar_tweets, search_tweets_by_embedding, count_with_embeddings

### Phase 2: Repository Implementations

**2.1 Create `src/tweet_ingestion/repositories/tweet_thread_repository.py`:**
- [ ] Pattern: Mirror `URLRepository` structure
- [ ] Deduplication by `root_tweet_id` in `add()`

**2.2 Create `src/tweet_ingestion/repositories/tweet_repository.py`:**
- [ ] Pattern: Mirror `URLChunkRepository` structure
- [ ] Vector similarity search: `find_similar_tweets()`, `search_tweets_by_embedding()`
- [ ] Random selection: `get_random()` using `func.random()`
- [ ] Deduplication by `tweet_id` in `add()`

### Phase 3: Twitter Fetching & Content Processing

**3.1 Create `src/tweet_ingestion/twitter_fetcher.py`:**
- [ ] Function: `async fetch_tweet(tweet_id: str) -> FetchedTweet`
- [ ] Function: `async fetch_thread(tweet_id: str, max_depth: int) -> FetchedThread`
- [ ] Parse tweet URLs to extract tweet ID
- [ ] Use Twitter API v2 with Bearer Token
- [ ] Handle rate limiting with exponential backoff
- [ ] Extract: text, author, media URLs, conversation ID
- [ ] Raise `TwitterFetchError` on failures

**3.2 Create `src/tweet_ingestion/tweet_processor.py`:**
- [ ] Function: `async process_tweet_content(...) -> TweetThreadWithTweetsResponse`
- [ ] Steps:
  1. Parse input (URL or tweet ID)
  2. Check if thread exists → return existing if found
  3. Fetch tweet/thread from Twitter API
  4. Generate thread summary via LLM (if multi-tweet)
  5. Parallel embedding generation for all tweets
  6. Save thread and tweets to database
  7. Return complete thread with all tweets

### Phase 4: Configuration & Dependencies

**4.1 Update `src/config.py`:**
- [ ] `twitter_bearer_token: SecretStr | None = None`
- [ ] `max_thread_depth: int = 50`
- [ ] `twitter_fetch_timeout: int = 30`
- [ ] `twitter_rate_limit_retries: int = 3`

**4.2 Update `src/dependencies.py`:**
- [ ] `get_tweet_thread_repository()`
- [ ] `get_tweet_repository()`
- [ ] `get_twitter_fetcher()`

**4.3 Update `src/test_utils.py`:**
- [ ] `StubTweetThreadRepository`
- [ ] `StubTweetRepository`
- [ ] `StubTwitterFetcher`

### Phase 5: Tweet-Specific Endpoints

**5.1 Create `src/routers/tweets.py`:**
- [ ] `POST /tweets` - Ingest tweet/thread (synchronous)
- [ ] `GET /tweets` - List all threads with tweet counts
- [ ] `GET /tweets/{thread_id}` - Get thread with all tweets
- [ ] `GET /tweets/{thread_id}/tweets/{tweet_id}` - SSE streaming with AI context

**5.2 Register router in `src/main.py`:**
- [ ] Import and include tweets router
- [ ] Add OpenAPI tag for documentation

### Phase 6: Unified Response Integration

**6.1 Update `src/routers/response_builders.py`:**
- [ ] `build_source_response_from_thread()` - TweetThread → TweetThreadSource
- [ ] `build_content_item_from_tweet()` - Tweet → TweetContent
- [ ] `build_unified_response_for_tweet()` - Combined tweet + thread + related tweets

**6.2 Update `src/routers/random_selector.py`:**
- [ ] Add tweet count to weighted selection
- [ ] Return tweets from random selection

**6.3 Update `src/routers/notes.py` `/random/v2`:**
- [ ] Handle tweet selection case
- [ ] Stream tweet with context using unified schema

### Phase 7: Search Integration

**7.1 Update `src/routers/search.py`:**
- [ ] Search tweets alongside notes and URL chunks
- [ ] Allocate portion of limit to tweets (1/3 or configurable)
- [ ] Group tweets by thread in results
- [ ] Update `SearchResult` model to include `tweet_threads` array

### Phase 8: Testing

**8.1 Unit Tests:**
- [ ] `src/tweet_ingestion/test_twitter_fetcher.py` - Fetching, parsing, error handling
- [ ] `src/tweet_ingestion/test_tweet_processor.py` - Processing pipeline

**8.2 Repository Tests:**
- [ ] `src/tweet_ingestion/repositories/test_tweet_thread_repository.py`
- [ ] `src/tweet_ingestion/repositories/test_tweet_repository.py`

**8.3 Router Tests:**
- [ ] `src/routers/test_tweets.py` - All tweet endpoints
- [ ] Update `src/routers/test_random_content.py` - Include tweets
- [ ] Update `src/routers/test_search.py` - Include tweets

**8.4 Add Test Fixtures:**
- [ ] Update `src/routers/conftest.py` with `setup_tweet_deps()`

### Phase 9: Documentation

**9.1 Update `CLAUDE.md`:**
- [ ] Add tweet endpoints to API documentation
- [ ] Update Key Files section
- [ ] Update testing patterns section

---

## Implementation Order

1. **Phase 1** (Models & Migration) - Foundation
2. **Phase 2** (Repositories) - Data access layer
3. **Phase 3** (Processing) - Twitter fetching and processing
4. **Phase 4** (Config & DI) - Wire dependencies
5. **Phase 5** (Endpoints) - Tweet-specific API
6. **Phase 6** (Integration) - Unified responses and random selection
7. **Phase 7** (Search) - Include in semantic search
8. **Phase 8** (Testing) - Comprehensive test coverage
9. **Phase 9** (Documentation) - Update docs

---

## Open Questions for Review

### Q1: Twitter API Authentication
**Options:**
- A) Bearer Token only (app-only auth, read-only, simpler)
- B) OAuth 2.0 with user context (can access protected tweets)
- C) Support both with Bearer as default

**Recommendation:** Option A (Bearer Token only) for simplicity. Protected tweets require user auth which adds complexity.

### Q2: Thread vs Individual Tweet Focus
**Options:**
- A) Always fetch full thread when ingesting any tweet
- B) Option to ingest single tweet without thread context
- C) Ingest single tweet, but allow expanding to thread later

**Recommendation:** Option A - threads provide better context for AI generation.

### Q3: Media Handling
**Options:**
- A) Store media URLs only (no download)
- B) Download and store media locally
- C) Generate descriptions of images via vision model

**Recommendation:** Option A for MVP - store URLs, display in UI. Option C could be Phase 2 enhancement.

### Q4: Quote Tweets and Retweets
**Options:**
- A) Follow quote tweets and include quoted content
- B) Store reference only, don't expand
- C) Ignore quote tweets entirely

**Recommendation:** Option B - store as reference, expand could be future enhancement.

### Q5: Rate Limiting Strategy
**Options:**
- A) Fail fast on rate limit, return error
- B) Queue and retry with backoff
- C) Return partial results if rate limited mid-thread

**Recommendation:** Option B with reasonable timeout (30s total wait max).

### Q6: Minimum Tweet Embedding
**Options:**
- A) Embed all tweets regardless of length
- B) Only embed tweets above minimum character threshold
- C) Combine very short tweets for embedding

**Recommendation:** Option A - even short tweets can be meaningful for search.

---

## Technical Considerations

### Twitter API v2 Requirements
- Bearer Token for app-only authentication
- Endpoints needed:
  - `GET /2/tweets/:id` - Single tweet
  - `GET /2/tweets/:id?expansions=author_id` - With author data
  - `GET /2/tweets/search/recent?query=conversation_id:{id}` - Thread tweets
- Rate limits: 300 requests/15min (app-only)

### Error Handling
- `TwitterFetchError` for API failures
- `TweetNotFoundError` for deleted/private tweets
- `RateLimitError` with retry-after information
- `ThreadTooLargeError` if exceeds max_thread_depth

### Content Size Considerations
- Tweets: max 280 characters (minimal storage)
- Threads: up to 50 tweets × 280 chars = ~14KB text
- Media URLs: stored as JSON array, not fetched
- Much smaller than URL content (500KB limit)

---

## Critical Files Reference

**New Files:**
- `src/tweet_ingestion/twitter_fetcher.py` - Twitter API client
- `src/tweet_ingestion/tweet_processor.py` - Processing pipeline
- `src/tweet_ingestion/repositories/interfaces.py` - Repository contracts
- `src/tweet_ingestion/repositories/tweet_thread_repository.py`
- `src/tweet_ingestion/repositories/tweet_repository.py`
- `src/routers/tweets.py` - Tweet endpoints

**Modified Files:**
- `src/repositories/models.py` - Add Tweet/TweetThread models
- `src/routers/response_builders.py` - Add tweet builders
- `src/routers/random_selector.py` - Add tweet selection
- `src/routers/notes.py` - Update /random/v2
- `src/routers/search.py` - Include tweets
- `src/dependencies.py` - Add tweet dependencies
- `src/config.py` - Add Twitter settings
- `src/test_utils.py` - Add stub repositories

---

## Progress Summary

**Status:** Planning - Awaiting Review

**Next Steps after approval:**
1. Set up Twitter Developer account and obtain Bearer Token
2. Begin Phase 1: Models & Migration
3. Implement incrementally following URL ingestion patterns

---

*Plan Status: **DRAFT - PENDING REVIEW***

*Created: 2026-01-24*

*Last Updated: 2026-01-24*
