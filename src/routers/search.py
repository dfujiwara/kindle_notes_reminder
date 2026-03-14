"""
Search endpoints for semantic search across notes and URL chunks using AI embeddings.
"""

import asyncio
from fastapi import APIRouter, Depends
from src.repositories.models import (
    BookResponse,
    NoteResponse,
    BookWithNoteResponses,
    NoteRead,
    URLResponse,
    URLChunkResponse,
    URLWithChunksResponses,
    URLChunkRead,
    SearchResult,
)
from src.repositories.interfaces import (
    BookRepositoryInterface,
    NoteRepositoryInterface,
)
from src.url_ingestion.repositories.interfaces import (
    URLRepositoryInterface,
    URLChunkRepositoryInterface,
)
from src.embedding_interface import EmbeddingClientInterface
from src.dependencies import (
    get_book_repository,
    get_note_repository,
    get_url_repository,
    get_urlchunk_repository,
    get_embedding_client,
)

router = APIRouter(tags=["search"])


def _group_and_fetch_notes(
    similar_notes: list[NoteRead],
    book_repository: BookRepositoryInterface,
) -> list[BookWithNoteResponses]:
    """
    Group notes by book and fetch related book information.

    Args:
        similar_notes: List of similar notes from embedding search
        book_repository: Repository for fetching book details

    Returns:
        List of BookWithNoteResponses grouped by book
    """
    books_dict: dict[int, BookWithNoteResponses] = {}

    if not similar_notes:
        return []

    book_ids = [n.book_id for n in similar_notes]
    fetched_books = book_repository.get_by_ids(book_ids)
    fetched_books_dict = {b.id: b for b in fetched_books}

    for note in similar_notes:
        book_id = note.book_id
        if book_id not in books_dict:
            fetched_book = fetched_books_dict[book_id]
            book_response = BookResponse(
                id=note.book_id,
                title=fetched_book.title,
                author=fetched_book.author,
                created_at=fetched_book.created_at,
            )
            books_dict[book_id] = BookWithNoteResponses(book=book_response, notes=[])
        books_dict[book_id].notes.append(
            NoteResponse(id=note.id, content=note.content, created_at=note.created_at)
        )

    return list(books_dict.values())


def _group_and_fetch_chunks(
    similar_chunks: list[URLChunkRead],
    url_repository: URLRepositoryInterface,
) -> list[URLWithChunksResponses]:
    """
    Group URL chunks by URL and fetch related URL information.

    Args:
        similar_chunks: List of similar chunks from embedding search
        url_repository: Repository for fetching URL details

    Returns:
        List of URLWithChunksResponses grouped by URL
    """
    urls_dict: dict[int, URLWithChunksResponses] = {}

    if not similar_chunks:
        return []

    url_ids = [c.url_id for c in similar_chunks]
    fetched_urls = url_repository.get_by_ids(url_ids)
    fetched_urls_dict = {u.id: u for u in fetched_urls}

    for chunk in similar_chunks:
        url_id = chunk.url_id
        if url_id not in urls_dict:
            fetched_url = fetched_urls_dict[url_id]
            url_response = URLResponse(
                id=url_id,
                url=fetched_url.url,
                title=fetched_url.title,
                fetched_at=fetched_url.fetched_at,
                created_at=fetched_url.created_at,
            )
            urls_dict[url_id] = URLWithChunksResponses(url=url_response, chunks=[])
        urls_dict[url_id].chunks.append(
            URLChunkResponse(
                id=chunk.id,
                content=chunk.content,
                chunk_order=chunk.chunk_order,
                is_summary=chunk.is_summary,
                created_at=chunk.created_at,
            )
        )

    return list(urls_dict.values())


@router.get(
    "/search",
    summary="Semantic search across notes and URL content",
    description="""
    Search for notes and URL content using semantic search based on the provided query.

    This endpoint:
    - Converts your search query into embeddings using OpenAI
    - Finds semantically similar notes and URL chunks using vector similarity
    - Groups notes by book and chunks by URL for better organization
    - Returns results with similarity scores above the threshold
    """,
    response_description="Search results grouped by book/URL with similarity scores",
    responses={
        200: {"description": "Search completed successfully"},
        422: {"description": "Invalid query parameters"},
    },
)
async def search(
    q: str,
    limit: int = 10,
    book_repository: BookRepositoryInterface = Depends(get_book_repository),
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
    url_repository: URLRepositoryInterface = Depends(get_url_repository),
    urlchunk_repository: URLChunkRepositoryInterface = Depends(get_urlchunk_repository),
    embedding_client: EmbeddingClientInterface = Depends(get_embedding_client),
) -> SearchResult:
    # Validate limit
    limit = min(limit, 50)

    # Generate embedding for the search query
    query_embedding = await embedding_client.generate_embedding(q)

    # Search repositories sequentially to avoid session concurrency issues
    # Both are already ordered by relevance (similarity score ascending)
    similar_notes = await asyncio.to_thread(
        note_repository.search_notes_by_embedding,
        query_embedding,
        limit,
        0.7,
    )
    similar_chunks = await asyncio.to_thread(
        urlchunk_repository.search_chunks_by_embedding,
        query_embedding,
        limit,
        0.7,
    )

    # Group and fetch related data
    books_results = _group_and_fetch_notes(similar_notes, book_repository)
    urls_results = _group_and_fetch_chunks(similar_chunks, url_repository)

    # Calculate total count
    total_count = sum(len(book.notes) for book in books_results) + sum(
        len(url.chunks) for url in urls_results
    )

    return SearchResult(
        query=q,
        results=books_results,  # For backwards compatibility
        books=books_results,
        urls=urls_results,
        count=total_count,
    )
