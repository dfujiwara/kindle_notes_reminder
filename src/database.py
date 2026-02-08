from contextlib import AbstractContextManager, contextmanager
from typing import Callable, Generator

from sqlmodel import create_engine, Session

from src.config import settings

# Create synchronous engine using settings
engine = create_engine(
    settings.database_url,
    echo=settings.db_echo,
)


# A callable that returns a context-managed Session which auto-commits on exit.
# Used by background tasks that need their own transaction scope.
SessionFactory = Callable[[], AbstractContextManager[Session]]


# Generator to provide DB sessions
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
        session.commit()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
        session.commit()
