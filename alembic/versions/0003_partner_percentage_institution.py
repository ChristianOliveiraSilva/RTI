"""add partner_percentage to pis and institution to pi_authors

Revision ID: 0003_partner_pct
Revises: 0002_author_documents
Create Date: 2026-04-27 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_partner_pct"
down_revision: Union[str, None] = "0002_author_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pis", sa.Column("partner_percentage", sa.Numeric(5, 2), nullable=True))
    op.add_column("pi_authors", sa.Column("institution", sa.String(20), nullable=True, server_default="ifms"))


def downgrade() -> None:
    op.drop_column("pi_authors", "institution")
    op.drop_column("pis", "partner_percentage")
