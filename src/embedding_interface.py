from typing import Protocol
from src.types import Embedding


class EmbeddingError(Exception):
    """Base exception class for all embedding-related errors"""

    pass


class EmbeddingClientInterface(Protocol):
    async def generate_embedding(self, content: str) -> Embedding:
        """
        Generate an embedding for the given content.

        Args:
            content: The text content to generate an embedding for.

        Returns:
            An embedding vector (list of floats).

        Raises:
            EmbeddingError: If there's an error generating the embedding.
        """
        ...
