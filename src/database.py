from typing import Generator
from sqlmodel import create_engine, Session
from src.config import settings

# Create synchronous engine using settings
engine = create_engine(
    settings.database_url,
    echo=settings.db_echo,
)


# Generator to provide DB sessions
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
        session.commit()
