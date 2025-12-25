"""
URL content ingestion and processing pipeline.

Handles fetching URL content, chunking it, generating summaries and embeddings,
and storing everything in the database. Supports deduplication by URL.
"""

import asyncio
import hashlib
import logging

from src.url_ingestion.content_chunker import chunk_text_by_paragraphs
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
from src.url_ingestion.url_fetcher import URLFetchError, fetch_url_content

# Configure logging
logger = logging.getLogger(__name__)

# Summary generation settings
SUMMARY_CONTENT_LIMIT = 3000  # Characters to send to LLM for summary
MAX_CHUNK_SIZE = 1000  # Characters per chunk


async def process_url_content(
    url: str,
    url_repo: URLRepositoryInterface,
    chunk_repo: URLChunkRepositoryInterface,
    llm_client: LLMClientInterface,
    embedding_client: EmbeddingClientInterface,
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

    Returns:
        URLWithChunksResponses containing the URL and all chunks

    Raises:
        URLFetchError: If URL fetching or parsing fails
        Exception: If embedding generation or database operations fail
    """
    # Step 1: Check if URL already exists - return if found (deduplication)
    existing_url = url_repo.get_by_url(url)
    if existing_url:
        logger.info(f"URL already exists: {url}")
        # Fetch all chunks for this URL
        chunks_read = chunk_repo.get_by_url_id(existing_url.id)
        chunk_responses = [
            URLChunkResponse.model_validate(chunk) for chunk in chunks_read
        ]
        url_response = URLResponse.model_validate(existing_url)
        return URLWithChunksResponses(
            url=url_response,
            chunks=chunk_responses,
        )

    # Step 2: Fetch URL content
    logger.info(f"Fetching URL content: {url}")
    try:
        fetched = await fetch_url_content(url)
    except URLFetchError as e:
        logger.error(f"Failed to fetch URL {url}: {str(e)}")
        raise

    # Step 3: Save URL to database
    url_create = URLCreate(url=url, title=fetched.title)
    saved_url = url_repo.add(url_create)
    logger.info(f"Saved URL record with ID {saved_url.id}")

    # Step 4: Chunk content
    logger.info(f"Chunking content from {url}")
    chunks = chunk_text_by_paragraphs(fetched.content, max_chunk_size=MAX_CHUNK_SIZE)
    logger.info(f"Created {len(chunks)} text chunks from {url}")

    # Step 5: Generate summary from first portion of content
    logger.info(f"Generating summary for {url}")
    content_for_summary = fetched.content[:SUMMARY_CONTENT_LIMIT]
    summary = await _generate_summary(llm_client, content_for_summary)

    # Step 6: Prepare all content to embed (summary + text chunks)
    # Collect all content strings for embedding in order
    content_to_embed: list[tuple[str, int, bool, str | None]] = [
        (summary, 0, True, None),  # (content, chunk_order, is_summary, content_hash)
    ]

    # Add text chunks with their hashes
    for i, chunk in enumerate(chunks):
        # chunk_order starts at 1 for text chunks (0 is reserved for summary)
        content_to_embed.append((chunk.content, i + 1, False, chunk.content_hash))

    # Step 7: Generate embeddings in parallel
    logger.info(
        f"Generating {len(content_to_embed)} embeddings (summary + {len(chunks)} chunks)"
    )
    try:
        embedding_tasks = [
            embedding_client.generate_embedding(content)
            for content, _, _, _ in content_to_embed
        ]
        embeddings = await asyncio.gather(*embedding_tasks)
        logger.info("Successfully generated all embeddings")
    except Exception as e:
        logger.error(f"Error during parallel embedding generation: {str(e)}")
        raise

    # Step 8: Save chunks to database
    saved_chunks: list[URLChunkRead] = []
    for (content, chunk_order, is_summary, content_hash), embedding in zip(
        content_to_embed, embeddings
    ):
        # Generate or use existing hash
        if content_hash is None:
            # Summary chunk - generate hash from summary content
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        chunk_create = URLChunkCreate(
            content=content,
            content_hash=content_hash,
            url_id=saved_url.id,
            chunk_order=chunk_order,
            is_summary=is_summary,
            embedding=embedding,
        )
        saved_chunk = chunk_repo.add(chunk_create)
        saved_chunks.append(saved_chunk)
        logger.info(f"Saved chunk {chunk_order} (summary={is_summary}) to database")

    # Step 9: Build and return response
    url_response = URLResponse.model_validate(saved_url)
    chunk_responses = [URLChunkResponse.model_validate(chunk) for chunk in saved_chunks]

    logger.info(f"Successfully processed URL {url} with {len(chunk_responses)} chunks")
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
    prompt = f"""Please provide a concise 2-3 sentence summary of the following content:

{content}

Summary:"""

    system_instruction = (
        "You are a skilled summarizer. Generate clear, concise summaries that capture "
        "the most important information."
    )

    try:
        summary = await llm_client.get_response(prompt, system_instruction)
        logger.info(f"Generated summary: {summary[:100]}...")
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise
