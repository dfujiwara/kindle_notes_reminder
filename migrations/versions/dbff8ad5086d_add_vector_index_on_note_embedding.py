"""add vector index on note.embedding

Revision ID: dbff8ad5086d
Revises: 9b009926941d
Create Date: 2025-12-06 19:07:53.701368

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "dbff8ad5086d"
down_revision: Union[str, None] = "9b009926941d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create HNSW index for fast vector similarity search
    # HNSW is optimal for datasets < 1M vectors, provides fast queries
    # m=16 (default) - number of connections per layer
    # ef_construction=64 (default) - size of dynamic candidate list for construction
    op.execute(
        """
        CREATE INDEX ix_note_embedding_hnsw
        ON note
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_note_embedding_hnsw", table_name="note")
