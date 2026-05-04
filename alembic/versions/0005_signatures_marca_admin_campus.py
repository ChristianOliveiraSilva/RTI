"""add signing flow, marca fields, admin panel, campus, soft delete

Revision ID: 0005_sign_marca_admin_campus
Revises: 0004_anexo_i
Create Date: 2026-05-03 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_sign_marca_admin_campus"
down_revision: Union[str, None] = "0004_anexo_i"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

notification_type = sa.Enum("new_pi", "correction_submitted", name="notification_type")


def upgrade() -> None:
    # --- Enum extensions ---
    op.execute("ALTER TYPE pi_status ADD VALUE IF NOT EXISTS 'awaiting_signatures'")
    op.execute("ALTER TYPE pi_status ADD VALUE IF NOT EXISTS 'awaiting_corrections'")
    op.execute("ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'registro_marca'")

    # --- documents: signing support ---
    op.add_column("documents", sa.Column("is_signed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("documents", sa.Column("signed_file_path", sa.String(512), nullable=True))

    # --- author_profiles: campus ---
    op.add_column("author_profiles", sa.Column("campus", sa.String(50), nullable=True))

    # --- pis: software uploads ---
    op.add_column("pis", sa.Column("video_path", sa.String(512), nullable=True))
    op.add_column("pis", sa.Column("video_original_filename", sa.String(255), nullable=True))
    op.add_column("pis", sa.Column("source_code_path", sa.String(512), nullable=True))
    op.add_column("pis", sa.Column("source_code_original_filename", sa.String(255), nullable=True))

    # --- pis: admin/correction ---
    op.add_column("pis", sa.Column("admin_notes", sa.Text(), nullable=True))
    op.add_column("pis", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # --- pis: marca fields ---
    op.add_column("pis", sa.Column("marca_nome", sa.String(255), nullable=True))
    op.add_column("pis", sa.Column("marca_tipo", sa.String(50), nullable=True))
    op.add_column("pis", sa.Column("marca_imagem_path", sa.String(512), nullable=True))
    op.add_column("pis", sa.Column("marca_imagem_original_filename", sa.String(255), nullable=True))
    op.add_column("pis", sa.Column("marca_idioma_estrangeiro", sa.Boolean(), nullable=True, server_default=sa.text("false")))
    op.add_column("pis", sa.Column("marca_termo_estrangeiro", sa.String(255), nullable=True))
    op.add_column("pis", sa.Column("marca_traducao", sa.String(255), nullable=True))
    op.add_column("pis", sa.Column("marca_termos_colidencia", sa.Text(), nullable=True))
    op.add_column("pis", sa.Column("marca_nice", sa.String(255), nullable=True))
    op.add_column("pis", sa.Column("marca_viena", sa.String(255), nullable=True))
    op.add_column("pis", sa.Column("marca_protecao_indicada", sa.Boolean(), nullable=True))
    op.add_column("pis", sa.Column("marca_protecao_justificativa", sa.Text(), nullable=True))

    # --- admin_notifications table ---
    op.create_table(
        "admin_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pi_id", sa.Integer(), sa.ForeignKey("pis.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_admin_notifications_is_read", "admin_notifications", ["is_read"])


def downgrade() -> None:
    op.drop_index("ix_admin_notifications_is_read", table_name="admin_notifications")
    op.drop_table("admin_notifications")

    # pis: marca fields
    op.drop_column("pis", "marca_protecao_justificativa")
    op.drop_column("pis", "marca_protecao_indicada")
    op.drop_column("pis", "marca_viena")
    op.drop_column("pis", "marca_nice")
    op.drop_column("pis", "marca_termos_colidencia")
    op.drop_column("pis", "marca_traducao")
    op.drop_column("pis", "marca_termo_estrangeiro")
    op.drop_column("pis", "marca_idioma_estrangeiro")
    op.drop_column("pis", "marca_imagem_original_filename")
    op.drop_column("pis", "marca_imagem_path")
    op.drop_column("pis", "marca_tipo")
    op.drop_column("pis", "marca_nome")

    # pis: admin/correction
    op.drop_column("pis", "deleted_at")
    op.drop_column("pis", "admin_notes")

    # pis: software uploads
    op.drop_column("pis", "source_code_original_filename")
    op.drop_column("pis", "source_code_path")
    op.drop_column("pis", "video_original_filename")
    op.drop_column("pis", "video_path")

    # author_profiles
    op.drop_column("author_profiles", "campus")

    # documents
    op.drop_column("documents", "signed_file_path")
    op.drop_column("documents", "is_signed")

    bind = op.get_bind()
    notification_type.drop(bind, checkfirst=True)
