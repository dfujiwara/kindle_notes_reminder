import os
from typing import Generator
from sqlmodel import SQLModel, create_engine
from sqlalchemy.orm import sessionmaker, Session

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

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# Function to create all tables
def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)

# Generator to provide DB sessions
def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session