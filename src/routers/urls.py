"""
URL-related endpoints for ingesting and exploring URLs with AI enhancements.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel, Field
from pydantic import HttpUrl
from src.url_ingestion.repositories.interfaces import (
    URLRepositoryInterface,
    URLChunkRepositoryInterface,
)
from src.llm_interface import LLMClientInterface
from src.embedding_interface import EmbeddingClientInterface
from src.url_ingestion.url_fetcher import URLFetcherInterface
from src.dependencies import (
    get_url_repository,
    get_urlchunk_repository,
    get_llm_client,
    get_embedding_client,
    get_url_fetcher,
)
from src.repositories.models import (
    URLWithChunksResponses,
    URLWithChunksResponse,
)
from src.url_ingestion.url_processor import process_url_content
from src.url_ingestion.url_fetcher import URLFetchError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["urls"])


class URLIngestRequest(SQLModel):
    """Request model for URL ingestion."""

    url: HttpUrl = Field(description="URL to ingest and process")


class URLListResponse(SQLModel):
    """Response model for listing URLs with chunk counts."""

    urls: list[URLWithChunksResponse]


@router.post(
    "/urls",
    summary="Ingest URL content",
    description="""
    Process and store URL content with chunking and embeddings.

    This endpoint:
    - Fetches content from the provided URL
    - Chunks the content into semantic sections
    - Generates AI summary and embeddings
    - Stores everything with deduplication

    If the URL has already been ingested, returns the existing record without re-fetching.
    """,
    response_description="Processing result with URL and chunks",
    responses={
        422: {"description": "Cannot process URL (fetch error or no content)"},
        200: {"description": "URL processed successfully"},
    },
)
async def ingest_url(
    request: URLIngestRequest,
    url_repository: URLRepositoryInterface = Depends(get_url_repository),
    chunk_repository: URLChunkRepositoryInterface = Depends(get_urlchunk_repository),
    llm_client: LLMClientInterface = Depends(get_llm_client),
    embedding_client: EmbeddingClientInterface = Depends(get_embedding_client),
    url_fetcher: URLFetcherInterface = Depends(get_url_fetcher),
) -> URLWithChunksResponses:
    """Ingest and process URL content."""
    url_str = str(request.url)
    try:
        result = await process_url_content(
            url_str,
            url_repository,
            chunk_repository,
            llm_client,
            embedding_client,
            fetch_fn=url_fetcher,
        )
        return result
    except URLFetchError as e:
        logger.error(f"URL fetch error for {url_str}: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Cannot process URL: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error processing URL {url_str}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing URL: {str(e)}")


@router.get(
    "/urls",
    summary="List all URLs",
    description="Retrieve all processed URLs with their chunk counts",
    response_description="List of URLs with metadata and chunk counts",
    response_model=URLListResponse,
)
async def get_urls(
    url_repository: URLRepositoryInterface = Depends(get_url_repository),
    chunk_repository: URLChunkRepositoryInterface = Depends(get_urlchunk_repository),
) -> URLListResponse:
    """List all URLs with chunk counts."""
    urls = url_repository.list_urls()
    chunk_count_dict = chunk_repository.get_chunk_counts_by_url_ids(
        [u.id for u in urls]
    )

    url_responses: list[URLWithChunksResponse] = []
    for url in urls:
        url_responses.append(
            URLWithChunksResponse(
                id=url.id,
                url=url.url,
                title=url.title,
                fetched_at=url.fetched_at,
                created_at=url.created_at,
                chunk_count=chunk_count_dict.get(url.id, 0),
            )
        )

    return URLListResponse(urls=url_responses)
