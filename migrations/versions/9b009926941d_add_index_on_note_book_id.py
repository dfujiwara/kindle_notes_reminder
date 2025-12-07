"""add indexes on note.book_id and evaluation.note_id

Revision ID: 9b009926941d
Revises: 7d07e7c8e990
Create Date: 2025-12-06 18:58:37.793965

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9b009926941d"
down_revision: Union[str, None] = "7d07e7c8e990"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_note_book_id", "note", ["book_id"])
    op.create_index("ix_evaluation_note_id", "evaluation", ["note_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_evaluation_note_id", table_name="evaluation")
    op.drop_index("ix_note_book_id", table_name="note")
