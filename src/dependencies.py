"""
Dependency injection functions for FastAPI endpoints.

This module provides all the dependency functions used across the application,
following the Dependency Injection pattern to supply repository and client instances
to route handlers.
"""

from fastapi import Depends
from sqlmodel import Session
from src.database import get_session
from src.repositories.book_repository import BookRepository
from src.repositories.note_repository import NoteRepository
from src.repositories.evaluation_repository import EvaluationRepository
from src.url_ingestion.repositories.url_repository import URLRepository
from src.url_ingestion.repositories.urlchunk_repository import URLChunkRepository
from src.repositories.interfaces import (
    BookRepositoryInterface,
    NoteRepositoryInterface,
    EvaluationRepositoryInterface,
    URLRepositoryInterface,
    URLChunkRepositoryInterface,
)
from src.openai_client import OpenAIClient, OpenAIEmbeddingClient
from src.embedding_interface import EmbeddingClientInterface
from src.llm_interface import LLMClientInterface


def get_book_repository(
    session: Session = Depends(get_session),
) -> BookRepositoryInterface:
    """Get an instance of the book repository."""
    return BookRepository(session)


def get_note_repository(
    session: Session = Depends(get_session),
) -> NoteRepositoryInterface:
    """Get an instance of the note repository."""
    return NoteRepository(session)


def get_evaluation_repository(
    session: Session = Depends(get_session),
) -> EvaluationRepositoryInterface:
    """Get an instance of the evaluation repository."""
    return EvaluationRepository(session)


def get_embedding_client() -> EmbeddingClientInterface:
    """Get an instance of the embedding client."""
    return OpenAIEmbeddingClient()


def get_llm_client() -> LLMClientInterface:
    """Get an instance of the LLM client."""
    return OpenAIClient()


def get_url_repository(
    session: Session = Depends(get_session),
) -> URLRepositoryInterface:
    """Get an instance of the URL repository."""
    return URLRepository(session)


def get_urlchunk_repository(
    session: Session = Depends(get_session),
) -> URLChunkRepositoryInterface:
    """Get an instance of the URLChunk repository."""
    return URLChunkRepository(session)
