"""author documents (cpf/rg)

Revision ID: 0002_author_documents
Revises: 0001_initial
Create Date: 2026-04-26 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_author_documents"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


author_document_type = sa.Enum("cpf", "rg", name="author_document_type")


def upgrade() -> None:
    op.create_table(
        "author_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "pi_author_id",
            sa.Integer(),
            sa.ForeignKey("pi_authors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", author_document_type, nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("pi_author_id", "type", name="uq_author_documents_author_type"),
    )
    op.create_index("ix_author_documents_pi_author_id", "author_documents", ["pi_author_id"])


def downgrade() -> None:
    op.drop_index("ix_author_documents_pi_author_id", table_name="author_documents")
    op.drop_table("author_documents")

    bind = op.get_bind()
    author_document_type.drop(bind, checkfirst=True)

