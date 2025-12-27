"""
Tests for the additional_context module.

Tests the streaming version of get_additional_context.
"""

import pytest
from .additional_context import (
    get_additional_context_stream,
    get_additional_context_stream_for_chunk,
)
from src.prompts import create_context_prompt, create_chunk_context_prompt, SYSTEM_INSTRUCTIONS
from src.test_utils import StubLLMClient


@pytest.mark.asyncio
async def test_get_additional_context_stream_success():
    """Test that streaming yields multiple chunks and combines to full response."""
    # Create a long response that will be split into chunks
    long_response = "A" * 100  # 100 characters
    llm_client = StubLLMClient(responses=[long_response])

    # Prepare prompt and instruction
    prompt = create_context_prompt("Test Book", "Test content")
    instruction = SYSTEM_INSTRUCTIONS["context_provider"]

    chunks: list[str] = []
    final_chunk = None
    async for chunk in get_additional_context_stream(llm_client, prompt, instruction):
        if chunk.is_complete:
            final_chunk = chunk
        else:
            chunks.append(chunk.content)

    # Verify streaming behavior: StubLLMClient splits into chunks of size 10
    assert len(chunks) == 10
    assert all(len(chunk) == 10 for chunk in chunks)

    # Verify chunks combine to the full response
    assert "".join(chunks) == long_response

    # Verify we got the final chunk with metadata
    assert final_chunk is not None
    assert final_chunk.is_complete is True
    assert final_chunk.content == long_response
    assert final_chunk.llm_prompt_response is not None
    assert final_chunk.llm_prompt_response.response == long_response
    assert "Test Book" in final_chunk.llm_prompt_response.prompt
    assert "Test content" in final_chunk.llm_prompt_response.prompt

    # Verify LLM was called
    assert llm_client.call_count == 1


@pytest.mark.asyncio
async def test_get_additional_context_stream_for_chunk_success():
    """Test chunk context streaming generates proper prompts."""
    # Create response for chunk context
    chunk_response = "Explanation of the chunk" * 10  # Repeated to make it longer
    llm_client = StubLLMClient(responses=[chunk_response])

    # Use chunk-specific function
    url_title = "Python Tutorials"
    chunk_content = "Understanding decorators"

    chunks: list[str] = []
    final_chunk = None
    async for chunk in get_additional_context_stream_for_chunk(
        llm_client, url_title, chunk_content
    ):
        if chunk.is_complete:
            final_chunk = chunk
        else:
            chunks.append(chunk.content)

    # Verify streaming behavior
    assert len(chunks) > 0
    assert "".join(chunks) == chunk_response

    # Verify final chunk has proper metadata
    assert final_chunk is not None
    assert final_chunk.is_complete is True
    assert final_chunk.content == chunk_response
    assert final_chunk.llm_prompt_response is not None

    # Verify the prompt includes URL title and chunk content
    prompt = final_chunk.llm_prompt_response.prompt
    assert url_title in prompt
    assert chunk_content in prompt
    assert "Article:" in prompt
    assert "Content passage:" in prompt

    # Verify system instruction is the context_provider one
    system = final_chunk.llm_prompt_response.system
    assert system == SYSTEM_INSTRUCTIONS["context_provider"]

    # Verify LLM was called
    assert llm_client.call_count == 1
