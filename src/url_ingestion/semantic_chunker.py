"""
LLM-based semantic chunking for URL content.

This module provides semantic chunking using an LLM to extract main article content
and create semantically coherent chunks (complete ideas/sections).
"""

import json
import logging
from typing import Any, cast  # Any used in field_validator

from pydantic import BaseModel, field_validator

from src.llm_interface import LLMClientInterface, LLMError
from src.prompts import SYSTEM_INSTRUCTIONS, create_semantic_chunking_prompt

logger = logging.getLogger(__name__)

# Maximum content size in characters (~25K tokens for gpt-4o-mini)
MAX_CONTENT_SIZE = 100_000


class SemanticChunkingError(Exception):
    """Exception raised when semantic chunking fails."""

    pass


class SemanticChunkingResult(BaseModel):
    """Result of semantic chunking containing extracted content chunks."""

    chunks: list[str]

    @field_validator("chunks", mode="before")
    @classmethod
    def filter_and_strip_chunks(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            raise ValueError("'chunks' field must be a list")
        items = cast(list[Any], v)
        stripped = [
            chunk.strip() for chunk in items if isinstance(chunk, str) and chunk.strip()
        ]
        if not stripped:
            raise ValueError("chunks must contain at least one non-empty string")
        return stripped


def _parse_llm_response(response: str) -> SemanticChunkingResult:
    """
    Parse and validate LLM response, handling potential markdown code blocks.

    Args:
        response: Raw LLM response string

    Returns:
        Validated SemanticChunkingResult

    Raises:
        SemanticChunkingError: If response is not valid JSON or fails validation
    """
    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        raise SemanticChunkingError(
            f"Failed to parse LLM response as JSON: {response[:200]}"
        ) from e

    try:
        return SemanticChunkingResult(**data)
    except ValueError as e:
        raise SemanticChunkingError(f"Invalid chunking result: {e}") from e


async def chunk_content_with_llm(
    llm_client: LLMClientInterface, content: str
) -> SemanticChunkingResult:
    """
    Extract and chunk content using an LLM for semantic understanding.

    This function sends the content to an LLM which extracts the main article
    content (filtering out navigation, sidebars, etc.) and creates semantically
    coherent chunks.

    Args:
        llm_client: LLM client interface for making requests
        content: Raw content to process

    Returns:
        SemanticChunkingResult containing the extracted chunks

    Raises:
        SemanticChunkingError: If chunking fails (LLM error, invalid response, etc.)
    """
    # Handle very short content
    if len(content.strip()) < 50:
        raise SemanticChunkingError("Content too short for semantic chunking")

    # Truncate content if too large
    if len(content) > MAX_CONTENT_SIZE:
        logger.warning(
            f"Content size ({len(content)} chars) exceeds limit, "
            f"truncating to {MAX_CONTENT_SIZE} chars"
        )
        content = content[:MAX_CONTENT_SIZE]

    # Get LLM response with JSON mode
    try:
        prompt = create_semantic_chunking_prompt(content)
        instruction = SYSTEM_INSTRUCTIONS["semantic_chunker"]
        response = await llm_client.get_response(prompt, instruction, json_mode=True)
    except LLMError as e:
        raise SemanticChunkingError(f"LLM request failed: {e}") from e

    # Parse and validate response
    return _parse_llm_response(response)
