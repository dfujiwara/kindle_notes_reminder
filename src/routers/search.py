"""
Search endpoints for semantic search across notes using AI embeddings.
"""

from fastapi import APIRouter, Depends
from src.repositories.models import (
    BookResponse,
    NoteResponse,
    BookWithNoteResponses,
    SearchResult,
)
from src.repositories.interfaces import (
    BookRepositoryInterface,
    NoteRepositoryInterface,
)
from src.embedding_interface import EmbeddingClientInterface
from src.dependencies import (
    get_book_repository,
    get_note_repository,
    get_embedding_client,
)

router = APIRouter(tags=["search"])


@router.get(
    "/search",
    summary="Semantic search across notes",
    description="""
    Search for notes using semantic search based on the provided query.

    This endpoint:
    - Converts your search query into embeddings using OpenAI
    - Finds semantically similar notes using vector similarity
    - Groups results by book for better organization
    - Returns results with similarity scores above the threshold
    """,
    response_description="Search results grouped by book with similarity scores",
    responses={
        200: {"description": "Search completed successfully"},
        422: {"description": "Invalid query parameters"},
    },
)
async def search_notes(
    q: str,
    limit: int = 10,
    book_repository: BookRepositoryInterface = Depends(get_book_repository),
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
    embedding_client: EmbeddingClientInterface = Depends(get_embedding_client),
) -> SearchResult:
    # Validate limit
    limit = min(limit, 50)

    # Generate embedding for the search query
    query_embedding = await embedding_client.generate_embedding(q)

    # Search for similar notes
    similar_notes = note_repository.search_notes_by_embedding(
        query_embedding, limit=limit, similarity_threshold=0.7
    )

    book_ids = [n.book_id for n in similar_notes]
    fetched_books = book_repository.get_by_ids(book_ids)
    fetched_books_dict = {b.id: b for b in fetched_books}
    # Group notes by book
    books_dict: dict[int, BookWithNoteResponses] = {}

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

    results = list(books_dict.values())
    total_notes = sum(len(book.notes) for book in results)

    return SearchResult(query=q, results=results, count=total_notes)
