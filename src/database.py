from typing import Generator
from sqlmodel import SQLModel, create_engine, Session
from src.config import settings

# Create synchronous engine using settings
engine = create_engine(
    settings.database_url,
    echo=settings.db_echo,
)


# Function to create all tables
def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


# Generator to provide DB sessions
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
