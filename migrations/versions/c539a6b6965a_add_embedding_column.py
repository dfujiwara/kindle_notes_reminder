"""add_embedding_column

Revision ID: c539a6b6965a
Revises: 733289f694be
Create Date: 2024-03-19 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "c539a6b6965a"
down_revision: Union[str, None] = "733289f694be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable the vector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add the embedding column
    op.add_column("note", sa.Column("embedding", Vector(1536), nullable=True))


def downgrade() -> None:
    # Remove the embedding column
    op.drop_column("note", "embedding")

    # Note: We don't drop the vector extension as it might be used by other tables
