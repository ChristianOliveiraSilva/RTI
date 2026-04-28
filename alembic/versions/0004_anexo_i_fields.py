"""add Anexo I fields to pis table and anexo_i to document_type enum

Revision ID: 0004_anexo_i
Revises: 0003_partner_pct
Create Date: 2026-04-27 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_anexo_i"
down_revision: Union[str, None] = "0003_partner_pct"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("pis", sa.Column("programming_language", sa.String(255), nullable=True))
    op.add_column("pis", sa.Column("creation_date", sa.Date(), nullable=True))
    op.add_column("pis", sa.Column("publication_date", sa.Date(), nullable=True))
    op.add_column("pis", sa.Column("application_field", sa.String(500), nullable=True))
    op.add_column("pis", sa.Column("program_type", sa.String(500), nullable=True))
    op.add_column("pis", sa.Column("source_hash", sa.String(512), nullable=True))
    op.add_column("pis", sa.Column("is_derived", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("pis", sa.Column("derived_title", sa.String(500), nullable=True))
    op.add_column("pis", sa.Column("derived_registration", sa.String(255), nullable=True))

    op.execute("ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'anexo_i'")

def downgrade() -> None:
    op.drop_column("pis", "derived_registration")
    op.drop_column("pis", "derived_title")
    op.drop_column("pis", "is_derived")
    op.drop_column("pis", "source_hash")
    op.drop_column("pis", "program_type")
    op.drop_column("pis", "application_field")
    op.drop_column("pis", "publication_date")
    op.drop_column("pis", "creation_date")
    op.drop_column("pis", "programming_language")
