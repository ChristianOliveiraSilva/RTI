"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-25 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role = sa.Enum("admin", "author", name="user_role")
pi_status = sa.Enum("draft", "awaiting_authors", "completed", name="pi_status")
pi_author_status = sa.Enum("pending", "completed", name="pi_author_status")
pi_type = sa.Enum(
    "software", "patente", "desenho_industrial", "marca",
    "cultivar", "topografia", "outro", name="pi_type",
)
ifms_bond = sa.Enum("servidor", "estudante", "outros", name="ifms_bond")
document_type = sa.Enum("anexo_ii", "anexo_iii", "anexo_iv", "anexo_v", name="document_type")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="author"),
        sa.Column("google_sub", sa.String(255), nullable=True),
        sa.Column("picture", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("google_sub", name="uq_users_google_sub"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "pis",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("type", pi_type, nullable=False),
        sa.Column("has_partner", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("partner_name", sa.String(255), nullable=True),
        sa.Column("partner_cnpj", sa.String(32), nullable=True),
        sa.Column("partner_contact", sa.String(255), nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", pi_status, nullable=False, server_default="awaiting_authors"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "pi_authors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pi_id", sa.Integer(), sa.ForeignKey("pis.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", pi_author_status, nullable=False, server_default="pending"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("pi_id", "email", name="uq_pi_author_email"),
    )
    op.create_index("ix_pi_authors_email", "pi_authors", ["email"])

    op.create_table(
        "author_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pi_author_id", sa.Integer(), sa.ForeignKey("pi_authors.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("cpf", sa.String(20), nullable=False),
        sa.Column("rg", sa.String(30), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("nationality", sa.String(80), nullable=False),
        sa.Column("marital_status", sa.String(40), nullable=False),
        sa.Column("occupation", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("cellphone", sa.String(30), nullable=False),
        sa.Column("address_street", sa.String(200), nullable=False),
        sa.Column("address_number", sa.String(20), nullable=False),
        sa.Column("address_district", sa.String(120), nullable=False),
        sa.Column("address_city", sa.String(120), nullable=False),
        sa.Column("address_state", sa.String(2), nullable=False),
        sa.Column("address_zip", sa.String(15), nullable=False),
        sa.Column("ifms_bond", ifms_bond, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "author_declarations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pi_author_id", sa.Integer(), sa.ForeignKey("pi_authors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("accepted_truth", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("accepted_confidentiality", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("accepted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pi_author_id", sa.Integer(), sa.ForeignKey("pi_authors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(96), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token", name="uq_invitations_token"),
    )
    op.create_index("ix_invitations_token", "invitations", ["token"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pi_id", sa.Integer(), sa.ForeignKey("pis.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", document_type, nullable=False),
        sa.Column("pdf_path", sa.String(512), nullable=False),
        sa.Column("pi_author_id", sa.Integer(), sa.ForeignKey("pi_authors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_index("ix_invitations_token", table_name="invitations")
    op.drop_table("invitations")
    op.drop_table("author_declarations")
    op.drop_table("author_profiles")
    op.drop_index("ix_pi_authors_email", table_name="pi_authors")
    op.drop_table("pi_authors")
    op.drop_table("pis")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    for enum in (document_type, ifms_bond, pi_type, pi_author_status, pi_status, user_role):
        enum.drop(bind, checkfirst=True)
