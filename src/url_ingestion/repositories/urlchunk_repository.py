from sqlmodel import Session, select
from src.repositories.models import URLChunk, URLChunkCreate, URLChunkRead, URL
from .interfaces import URLChunkRepositoryInterface
from sqlalchemy import func, column, Integer
from src.types import Embedding


class URLChunkRepository(URLChunkRepositoryInterface):
    def __init__(self, session: Session):
        self.session = session

    def add(self, chunk: URLChunkCreate) -> URLChunkRead:
        # Check if a chunk with the same content hash exists
        statement = select(URLChunk).where(URLChunk.content_hash == chunk.content_hash)
        existing_chunk = self.session.exec(statement).first()

        if existing_chunk:
            return URLChunkRead.model_validate(existing_chunk)

        # If no existing chunk found, create a new one
        db_chunk = URLChunk.model_validate(chunk)
        self.session.add(db_chunk)
        self.session.commit()
        self.session.refresh(db_chunk)

        return URLChunkRead.model_validate(db_chunk)

    def get(self, chunk_id: int, url_id: int) -> URLChunkRead | None:
        statement = (
            select(URLChunk)
            .where(URLChunk.id == chunk_id)
            .where(URLChunk.url_id == url_id)
        )
        chunk = self.session.exec(statement).first()
        if not chunk:
            return None

        return URLChunkRead.model_validate(chunk)

    def get_by_id(self, chunk_id: int) -> URLChunkRead | None:
        chunk = self.session.get(URLChunk, chunk_id)
        if not chunk:
            return None

        return URLChunkRead.model_validate(chunk)

    def get_random(self) -> URLChunkRead | None:
        statement = select(URLChunk).join(URL).order_by(func.random()).limit(1)
        chunk = self.session.exec(statement).first()
        if not chunk:
            return None

        return URLChunkRead.model_validate(chunk)

    def get_by_url_id(self, url_id: int) -> list[URLChunkRead]:
        statement = (
            select(URLChunk)
            .where(URLChunk.url_id == url_id)
            .order_by(URLChunk.__table__.c.chunk_order)  # type: ignore
        )
        chunks = self.session.exec(statement)
        return [URLChunkRead.model_validate(chunk) for chunk in chunks]

    def find_similar_chunks(
        self, chunk: URLChunkRead, limit: int = 5, similarity_threshold: float = 0.5
    ) -> list[URLChunkRead]:
        """
        Find chunks similar to the given chunk using vector similarity.
        Only searches within the same URL as the input chunk.

        Args:
            chunk: The chunk to find similar chunks for
            limit: Maximum number of similar chunks to return (default: 5)
            similarity_threshold: Maximum cosine distance to consider chunks similar (default: 0.5)
                                Lower values mean more similar (0 = identical, 1 = completely different)

        Returns:
            A list of similar chunks from the same URL, ordered by similarity (most similar first)
        """
        if chunk.embedding is None:
            return []

        distance = URLChunk.embedding_cosine_distance(chunk.embedding)

        statement = (
            select(URLChunk)
            .where(URLChunk.id != chunk.id)
            .where(URLChunk.url_id == chunk.url_id)
            .where(URLChunk.embedding_is_not_null())
            .where(distance <= similarity_threshold)
            .order_by(distance)
            .limit(limit)
        )

        chunks = self.session.exec(statement)
        return [URLChunkRead.model_validate(chunk) for chunk in chunks]

    def search_chunks_by_embedding(
        self, embedding: Embedding, limit: int = 10, similarity_threshold: float = 0.5
    ) -> list[URLChunkRead]:
        """
        Search for chunks similar to the given embedding across all URLs.

        Args:
            embedding: The embedding vector to search for
            limit: Maximum number of chunks to return (default: 10)
            similarity_threshold: Maximum cosine distance to consider chunks similar (default: 0.5)
                                Lower values mean more similar (0 = identical, 1 = completely different)

        Returns:
            A list of similar chunks from all URLs, ordered by similarity (most similar first)
        """
        distance = URLChunk.embedding_cosine_distance(embedding)

        statement = (
            select(URLChunk)
            .join(URL)
            .where(URLChunk.embedding_is_not_null())
            .where(distance <= similarity_threshold)
            .order_by(distance)
            .limit(limit)
        )

        chunks = self.session.exec(statement)
        return [URLChunkRead.model_validate(chunk) for chunk in chunks]

    def get_chunk_counts_by_url_ids(self, url_ids: list[int]) -> dict[int, int]:
        """
        Get the count of chunks for each URL ID in the given list.

        Args:
            url_ids: List of URL IDs to get chunk counts for

        Returns:
            Dictionary mapping url_id to chunk count. URLs with no chunks won't appear in the result.
        """
        if not url_ids:
            return {}

        # Create column expressions that work with the type system
        url_id_col = column("url_id", Integer)

        statement = (
            select(url_id_col, func.count())
            .select_from(URLChunk)
            .where(url_id_col.in_(url_ids))
            .group_by(url_id_col)
        )

        results = self.session.exec(statement)
        return {url_id: count for url_id, count in results}

    def count_with_embeddings(self) -> int:
        """
        Count chunks that have embeddings.

        Used for weighted random selection to ensure proportional distribution
        between notes and URL chunks in the unified /random endpoint.

        Returns:
            Number of chunks with non-null embeddings
        """
        statement = (
            select(func.count())
            .select_from(URLChunk)
            .where(URLChunk.embedding_is_not_null())
        )

        count = self.session.exec(statement).first()
        return count or 0
