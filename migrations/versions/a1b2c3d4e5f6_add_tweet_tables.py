"""add tweet and tweetthread tables

Revision ID: a1b2c3d4e5f6
Revises: fb012279fd22
Create Date: 2026-01-24 21:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "fb012279fd22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create tweetthread table first (parent table)
    op.create_table(
        "tweetthread",
        sa.Column("root_tweet_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "author_username", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "author_display_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tweet_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("root_tweet_id", name="uix_root_tweet_id"),
    )

    # Create tweet table (child table with foreign key to tweetthread)
    op.create_table(
        "tweet",
        sa.Column("tweet_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "author_username", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "author_display_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("media_urls", sa.JSON(), nullable=True),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("position_in_thread", sa.Integer(), nullable=False),
        sa.Column("tweeted_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "embedding", pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["tweetthread.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tweet_id", name="uix_tweet_id"),
    )

    # Create HNSW index on tweet embedding for fast similarity search
    op.execute(
        """
        CREATE INDEX ix_tweet_embedding_hnsw
        ON tweet
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_tweet_embedding_hnsw", table_name="tweet")
    op.drop_table("tweet")
    op.drop_table("tweetthread")
