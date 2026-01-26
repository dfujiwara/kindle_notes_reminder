# LLM-Based Semantic Chunking for URL Ingestion

## Problem
The current paragraph-based chunking extracts unwanted content (navigation, sidebars, related articles, author bios) even after removing common HTML tags. For blog posts/essays, chunks often cut off mid-thought or include boilerplate.

## Solution
Replace paragraph-based chunking with LLM-based semantic chunking that:
1. Extracts only main article content (filters boilerplate)
2. Creates semantically coherent chunks (complete ideas/sections)

Summary generation remains separate (existing `_generate_summary()` unchanged) for reliability.

## Implementation Steps

### Phase 0: Add JSON Mode to LLM Interface

**Modify: `src/llm_interface.py`**

Add `json_mode` parameter to guarantee valid JSON responses:
```python
@abstractmethod
async def get_response(
    self, prompt: str, instruction: str, json_mode: bool = False
) -> str:
```

**Modify: `src/openai_client.py`**

Update to use OpenAI's JSON mode when requested:
```python
response_format={"type": "json_object"} if json_mode else NOT_GIVEN
```

**Modify: `src/test_utils.py`**

Update `StubLLMClient` signature to match interface.

### Phase 1: Create Semantic Chunker Module

**New file: `src/url_ingestion/semantic_chunker.py`**

1. Define Pydantic model for structured output:
```python
class SemanticChunkingResult(BaseModel):
    chunks: list[str]  # Simple content strings
```

2. Implement `chunk_content_with_llm(llm_client, content) -> SemanticChunkingResult`:
   - Send content to LLM with `json_mode=True` for guaranteed valid JSON
   - Parse JSON response
   - Validate result structure (non-empty chunks)

3. Content size handling:
   - If content > 100K chars (~25K tokens): truncate to 100K chars
   - Log warning when truncation occurs
   - Rationale: gpt-4o-mini has 128K context, leave room for prompt + response

4. Add `SemanticChunkingError` exception class

### Phase 2: Add Prompts

**Modify: `src/prompts.py`**

Add system instruction:
```python
SYSTEM_INSTRUCTIONS["semantic_chunker"] = """You are a precise content extraction and semantic chunking assistant.
Extract main article content, ignore boilerplate (nav, sidebars, related articles, ads, comments).
Always respond with valid JSON."""
```

Add prompt function:
```python
def create_semantic_chunking_prompt(content: str) -> str:
    # Instructions for:
    # 1. Extract main content only
    # 2. Create semantic chunks (200-800 chars target)
    # 3. Each chunk should contain a complete thought or idea
    # Output JSON schema: {"chunks": ["chunk 1", "chunk 2", ...]}
```

### Phase 3: Integrate into URL Processor

**Modify: `src/url_ingestion/url_processor.py`**

Replace chunking logic in `process_url_content()`:

```python
# Before: paragraph-based chunking
chunks = chunk_text_by_paragraphs(fetched.content)

# After: LLM-based semantic chunking with fallback
try:
    result = await chunk_content_with_llm(llm_client, fetched.content)
    chunks = _convert_semantic_to_text_chunks(result.chunks)
except SemanticChunkingError:
    # Fallback to paragraph chunking
    chunks = chunk_text_by_paragraphs(fetched.content)

# Summary generation remains unchanged
summary = await _generate_summary(llm_client, fetched.content[:3000])
```

Add conversion function:
```python
def _convert_semantic_to_text_chunks(chunks: list[str]) -> list[TextChunk]:
    # Convert chunk strings to TextChunk format with content_hash
    # Preserves compatibility with URLChunk database model
```

### Phase 4: Add Tests

**New file: `src/url_ingestion/test_semantic_chunker.py`**

- `test_parse_llm_response_valid_json()`
- `test_parse_llm_response_json_in_code_block()`
- `test_parse_llm_response_invalid_json_raises()`
- `test_validate_empty_chunks_raises()`
- `test_chunk_very_short_content()`
- `test_semantic_chunking_with_stub_llm()`

**Modify: `src/url_ingestion/test_url_processor.py`**

- Update `StubLLMClient` to return valid semantic chunking JSON
- Add test for fallback to paragraph chunking

### Phase 5: Verification

1. Run `uv run ruff check && uv run ruff format`
2. Run `uv run pyright`
3. Run `uv run pytest -v`
4. Manual test with real URL:
   - Start services: `docker compose up -d`
   - Ingest a blog post: `POST /urls` with a real article URL
   - Verify chunks are clean (no nav/sidebar content)
   - Check chunk quality (semantic coherence)

## Files to Modify

| File | Change |
|------|--------|
| `src/llm_interface.py` | Add `json_mode` parameter to `get_response()` |
| `src/openai_client.py` | Implement JSON mode with `response_format` |
| `src/test_utils.py` | Update `StubLLMClient` signature |
| `src/url_ingestion/semantic_chunker.py` | **NEW** - Core LLM chunking logic |
| `src/url_ingestion/test_semantic_chunker.py` | **NEW** - Unit tests |
| `src/prompts.py` | Add `SYSTEM_INSTRUCTIONS["semantic_chunker"]` and `create_semantic_chunking_prompt()` |
| `src/url_ingestion/url_processor.py` | Replace chunking call, add fallback |
| `src/url_ingestion/test_url_processor.py` | Update for new chunking behavior |

## Key Design Decisions

1. **JSON mode** - Use OpenAI's `response_format={"type": "json_object"}` for guaranteed valid JSON
2. **Separate LLM calls** - Chunking and summary generation are separate for reliability
3. **Graceful fallback** - If LLM chunking fails, fall back to paragraph chunking
4. **Keep existing data model** - `TextChunk` and `URLChunk` unchanged for compatibility
5. **Simple output** - Just `chunks` list (no section_type/extraction_notes)
6. **100K char limit** - Truncate large content to fit LLM context window
7. **Target chunk size 200-800 chars** - Small enough for precise search, large enough for coherence

## No Migration Needed

- Database schema unchanged
- Existing URLs unaffected (deduplication by URL)
- Re-ingest URLs to apply new chunking
