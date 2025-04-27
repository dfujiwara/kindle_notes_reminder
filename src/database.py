import os
from typing import Generator
from sqlmodel import SQLModel, create_engine, Session

# Read DATABASE_URL environment variable or use default psycopg2 URL
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/fastapi"
)

# Create synchronous engine
engine = create_engine(
    DATABASE_URL,
    echo=True  # set to False in production
)

# Function to create all tables
def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)

# Generator to provide DB sessions
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session