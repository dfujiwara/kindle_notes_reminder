# LLM-Based Semantic Chunking for URL Ingestion

**Status: ✅ Fully implemented** (merged in #158)

## Problem
The current paragraph-based chunking extracts unwanted content (navigation, sidebars, related articles, author bios) even after removing common HTML tags. For blog posts/essays, chunks often cut off mid-thought or include boilerplate.

## Solution
Replace paragraph-based chunking with LLM-based semantic chunking that:
1. Extracts only main article content (filters boilerplate)
2. Creates semantically coherent chunks (complete ideas/sections)

Summary generation remains separate (existing `_generate_summary()` unchanged) for reliability.

## Implementation Summary

### Phase 0: JSON Mode in LLM Interface ✅
- `src/llm_interface.py` — `json_mode: bool = False` parameter on `get_response()`
- `src/openai_client.py` — `response_format={"type": "json_object"}` when `json_mode=True`
- `src/test_utils.py` — `StubLLMClient` signature updated

### Phase 1: Semantic Chunker Module ✅
- `src/url_ingestion/semantic_chunker.py` — `SemanticChunkingResult` model, `chunk_content_with_llm()`, `SemanticChunkingError`, content truncation at 100K chars, minimum content validation (50 chars)

### Phase 2: Prompts ✅
- `src/prompts.py` — `SYSTEM_INSTRUCTIONS["semantic_chunker"]` and `create_semantic_chunking_prompt()`

### Phase 3: URL Processor Integration ✅
- `src/url_ingestion/url_processor.py` — `_chunk_content()` tries semantic chunking first, falls back to paragraph chunking on `SemanticChunkingError`. `_convert_semantic_to_text_chunks()` converts to `TextChunk` format.

### Phase 4: Tests ✅
- `src/url_ingestion/test_semantic_chunker.py` — Result validation, LLM integration, error handling, truncation
- `src/url_ingestion/test_url_processor.py` — Success path, deduplication, fallback to paragraph chunking

## Files Modified

| File | Change |
|------|--------|
| `src/llm_interface.py` | Added `json_mode` parameter to `get_response()` |
| `src/openai_client.py` | Implemented JSON mode with `response_format` |
| `src/test_utils.py` | Updated `StubLLMClient` signature |
| `src/url_ingestion/semantic_chunker.py` | **NEW** — Core LLM chunking logic |
| `src/url_ingestion/test_semantic_chunker.py` | **NEW** — Unit tests |
| `src/prompts.py` | Added `SYSTEM_INSTRUCTIONS["semantic_chunker"]` and `create_semantic_chunking_prompt()` |
| `src/url_ingestion/url_processor.py` | Replaced chunking call, added fallback |
| `src/url_ingestion/test_url_processor.py` | Updated for new chunking behavior |

## Key Design Decisions

1. **JSON mode** — OpenAI's `response_format={"type": "json_object"}` for guaranteed valid JSON
2. **Separate LLM calls** — Chunking and summary generation are separate for reliability
3. **Graceful fallback** — If LLM chunking fails, fall back to paragraph chunking
4. **Keep existing data model** — `TextChunk` and `URLChunk` unchanged for compatibility
5. **Simple output** — Just `chunks` list (no section_type/extraction_notes)
6. **100K char limit** — Truncate large content to fit LLM context window
7. **Target chunk size 200-800 chars** — Small enough for precise search, large enough for coherence

## No Migration Needed

- Database schema unchanged
- Existing URLs unaffected (deduplication by URL)
- Re-ingest URLs to apply new chunking
