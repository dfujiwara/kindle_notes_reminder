"""
URL content ingestion and processing pipeline.

Handles fetching URL content, chunking it, generating summaries and embeddings,
and storing everything in the database. Supports deduplication by URL.
"""

import asyncio
import hashlib
import logging

from src.prompts import SYSTEM_INSTRUCTIONS, create_summary_prompt
from src.types import Embedding
from src.url_ingestion.content_chunker import TextChunk, chunk_text_by_paragraphs
from src.embedding_interface import EmbeddingClientInterface
from src.llm_interface import LLMClientInterface
from src.repositories.interfaces import (
    URLChunkRepositoryInterface,
    URLRepositoryInterface,
)
from src.repositories.models import (
    URLChunkCreate,
    URLChunkRead,
    URLChunkResponse,
    URLCreate,
    URLResponse,
    URLWithChunksResponses,
)
from src.url_ingestion.url_fetcher import (
    URLFetchError,
    URLFetcherInterface,
    fetch_url_content,
)

# Configure logging
logger = logging.getLogger(__name__)

# Summary generation settings
SUMMARY_CONTENT_LIMIT = 3000  # Characters to send to LLM for summary


async def process_url_content(
    url: str,
    url_repo: URLRepositoryInterface,
    chunk_repo: URLChunkRepositoryInterface,
    llm_client: LLMClientInterface,
    embedding_client: EmbeddingClientInterface,
    fetch_fn: URLFetcherInterface = fetch_url_content,
) -> URLWithChunksResponses:
    """
    Process URL content: fetch, chunk, summarize, embed, and store.

    This is a synchronous pipeline that blocks until all steps complete.
    If the URL already exists in the database, returns the existing record
    without re-fetching.

    Args:
        url: The URL to ingest
        url_repo: URL repository for database operations
        chunk_repo: URLChunk repository for database operations
        llm_client: LLM client for generating summaries
        embedding_client: Embedding client for generating vector embeddings
        fetch_fn: URL fetcher function (defaults to fetch_url_content)

    Returns:
        URLWithChunksResponses containing the URL and all chunks

    Raises:
        URLFetchError: If URL fetching or parsing fails
        Exception: If embedding generation or database operations fail
    """
    # Step 1: Check if URL already exists (deduplication)
    existing_result = _handle_existing_url(url, url_repo, chunk_repo)
    if existing_result:
        logger.info(f"URL already exists: {url}")
        return existing_result

    # Step 2: Fetch URL content
    logger.info(f"Fetching URL content: {url}")
    try:
        fetched = await fetch_fn(url)
    except URLFetchError as e:
        logger.error(f"Failed to fetch URL {url}: {str(e)}")
        raise

    # Step 3: Save URL to database
    url_create = URLCreate(url=url, title=fetched.title)
    saved_url = url_repo.add(url_create)
    logger.info(f"Saved URL record with ID {saved_url.id}")

    # Step 4: Chunk content and generate summary
    chunks = chunk_text_by_paragraphs(fetched.content)
    logger.info(f"Created {len(chunks)} text chunks from {url}")

    summary = await _generate_summary(
        llm_client, fetched.content[:SUMMARY_CONTENT_LIMIT]
    )
    logger.info(f"Generated summary for {url}")

    # Step 5: Prepare and embed content
    content_to_embed = _prepare_chunks_for_embedding(summary, chunks)
    embeddings = await _generate_all_embeddings(embedding_client, content_to_embed)

    # Step 6: Save chunks and return response
    saved_chunks = _save_chunks_to_database(
        chunk_repo, saved_url, content_to_embed, embeddings
    )
    result = _build_response(saved_url, saved_chunks, url)
    logger.info(f"Successfully processed URL {url} with {len(result.chunks)} chunks")
    return result


def _handle_existing_url(
    url: str,
    url_repo: URLRepositoryInterface,
    chunk_repo: URLChunkRepositoryInterface,
) -> URLWithChunksResponses | None:
    """Check if URL exists and return it if found (deduplication)."""
    existing_url = url_repo.get_by_url(url)
    if not existing_url:
        return None

    chunks_read = chunk_repo.get_by_url_id(existing_url.id)
    return _build_response(existing_url, chunks_read, url)


def _prepare_chunks_for_embedding(
    summary: str,
    chunks: list[TextChunk],
) -> list[TextChunk]:
    """Prepare summary and text chunks for embedding in proper order."""
    content_hash = hashlib.sha256(summary.encode("utf-8")).hexdigest()
    content_to_embed: list[TextChunk] = [
        TextChunk(
            content=summary,
            chunk_order=0,
            is_summary=True,
            content_hash=content_hash,
        ),
    ]

    for i, chunk in enumerate(chunks):
        content_to_embed.append(
            TextChunk(
                content=chunk.content,
                chunk_order=i + 1,
                is_summary=False,
                content_hash=chunk.content_hash,
            )
        )

    return content_to_embed


async def _generate_all_embeddings(
    embedding_client: EmbeddingClientInterface,
    content_to_embed: list[TextChunk],
) -> list[Embedding]:
    """Generate embeddings for all content in parallel."""
    logger.info(f"Generating {len(content_to_embed)} embeddings")
    try:
        embedding_tasks = [
            embedding_client.generate_embedding(chunk.content)
            for chunk in content_to_embed
        ]
        embeddings = await asyncio.gather(*embedding_tasks)
        logger.info("Successfully generated all embeddings")
        return embeddings
    except Exception as e:
        logger.error(f"Error during parallel embedding generation: {str(e)}")
        raise


def _save_chunks_to_database(
    chunk_repo: URLChunkRepositoryInterface,
    saved_url: URLResponse,
    content_to_embed: list[TextChunk],
    embeddings: list[Embedding],
) -> list[URLChunkRead]:
    """Save all chunks to database with their embeddings."""
    saved_chunks: list[URLChunkRead] = []

    for chunk, embedding in zip(content_to_embed, embeddings):
        chunk_create = URLChunkCreate(
            content=chunk.content,
            content_hash=chunk.content_hash,
            url_id=saved_url.id,
            chunk_order=chunk.chunk_order,
            is_summary=chunk.is_summary,
            embedding=embedding,
        )
        saved_chunk = chunk_repo.add(chunk_create)
        saved_chunks.append(saved_chunk)
        logger.info(
            f"Saved chunk {chunk.chunk_order} (summary={chunk.is_summary}) to database"
        )

    return saved_chunks


def _build_response(
    saved_url: URLResponse,
    saved_chunks: list[URLChunkRead],
    url: str,
) -> URLWithChunksResponses:
    """Build response from URL and chunks."""
    url_response = URLResponse.model_validate(saved_url)
    chunk_responses = [URLChunkResponse.model_validate(chunk) for chunk in saved_chunks]
    return URLWithChunksResponses(
        url=url_response,
        chunks=chunk_responses,
    )


async def _generate_summary(llm_client: LLMClientInterface, content: str) -> str:
    """
    Generate a 2-3 sentence summary of the given content using LLM.

    Args:
        llm_client: LLM client for generating summary
        content: Content to summarize

    Returns:
        Generated summary as string

    Raises:
        Exception: If summary generation fails
    """
    prompt = create_summary_prompt(content)
    system_instruction = SYSTEM_INSTRUCTIONS["summarizer"]

    try:
        summary = await llm_client.get_response(prompt, system_instruction)
        logger.info(f"Generated summary: {summary[:100]}...")
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise
