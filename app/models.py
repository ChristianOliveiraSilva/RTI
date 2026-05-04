from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    author = "author"


class PIStatus(str, enum.Enum):
    draft = "draft"
    awaiting_authors = "awaiting_authors"
    awaiting_signatures = "awaiting_signatures"
    awaiting_corrections = "awaiting_corrections"
    completed = "completed"


class PIAuthorStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"


class PIType(str, enum.Enum):
    software = "software"
    patente = "patente"
    desenho_industrial = "desenho_industrial"
    marca = "marca"
    cultivar = "cultivar"
    topografia = "topografia"
    outro = "outro"


class IfmsBond(str, enum.Enum):
    servidor = "servidor"
    estudante = "estudante"
    outros = "outros"


class DocumentType(str, enum.Enum):
    anexo_i = "anexo_i"
    anexo_ii = "anexo_ii"
    anexo_iii = "anexo_iii"
    anexo_iv = "anexo_iv"
    anexo_v = "anexo_v"
    registro_marca = "registro_marca"


class NotificationType(str, enum.Enum):
    new_pi = "new_pi"
    correction_submitted = "correction_submitted"


class AuthorDocumentType(str, enum.Enum):
    cpf = "cpf"
    rg = "rg"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.author, nullable=False
    )
    google_sub: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    picture: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    pis: Mapped[List["PI"]] = relationship(back_populates="owner")


class PI(Base):
    __tablename__ = "pis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[PIType] = mapped_column(Enum(PIType, name="pi_type"), nullable=False)

    has_partner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    partner_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    partner_cnpj: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    partner_contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    partner_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[PIStatus] = mapped_column(
        Enum(PIStatus, name="pi_status"), default=PIStatus.awaiting_authors, nullable=False
    )

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    programming_language: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    creation_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    publication_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    application_field: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    program_type: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_hash: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_derived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    derived_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    derived_registration: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Software-only uploads
    video_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    video_original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_code_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_code_original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Marca-only fields
    marca_nome: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    marca_tipo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    marca_imagem_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    marca_imagem_original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    marca_idioma_estrangeiro: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    marca_termo_estrangeiro: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    marca_traducao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    marca_termos_colidencia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    marca_nice: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    marca_viena: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    marca_protecao_indicada: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    marca_protecao_justificativa: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Admin / correction
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    owner: Mapped["User"] = relationship(back_populates="pis")
    authors: Mapped[List["PIAuthor"]] = relationship(
        back_populates="pi", cascade="all, delete-orphan", order_by="PIAuthor.id"
    )
    documents: Mapped[List["Document"]] = relationship(
        back_populates="pi", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["AdminNotification"]] = relationship(
        cascade="all, delete-orphan"
    )


class PIAuthor(Base):
    """Representa um (co)autor vinculado a uma PI.

    Substitui a antiga tabela ``authors``: os dados de identificação
    (name/email) ficam direto aqui, por PI.
    """

    __tablename__ = "pi_authors"
    __table_args__ = (UniqueConstraint("pi_id", "email", name="uq_pi_author_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pi_id: Mapped[int] = mapped_column(ForeignKey("pis.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    percentage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    institution: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="ifms")
    status: Mapped[PIAuthorStatus] = mapped_column(
        Enum(PIAuthorStatus, name="pi_author_status"),
        default=PIAuthorStatus.pending,
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pi: Mapped["PI"] = relationship(back_populates="authors")
    profile: Mapped[Optional["AuthorProfile"]] = relationship(
        back_populates="pi_author", uselist=False, cascade="all, delete-orphan"
    )
    declarations: Mapped[List["AuthorDeclaration"]] = relationship(
        back_populates="pi_author", cascade="all, delete-orphan"
    )
    invitations: Mapped[List["Invitation"]] = relationship(
        back_populates="pi_author", cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(
        back_populates="pi_author"
    )
    personal_documents: Mapped[List["AuthorDocument"]] = relationship(
        back_populates="pi_author", cascade="all, delete-orphan"
    )


class AuthorProfile(Base):
    __tablename__ = "author_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pi_author_id: Mapped[int] = mapped_column(
        ForeignKey("pi_authors.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    cpf: Mapped[str] = mapped_column(String(20), nullable=False)
    rg: Mapped[str] = mapped_column(String(30), nullable=False)
    birth_date: Mapped[Date] = mapped_column(Date, nullable=False)
    nationality: Mapped[str] = mapped_column(String(80), nullable=False)
    marital_status: Mapped[str] = mapped_column(String(40), nullable=False)
    occupation: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    cellphone: Mapped[str] = mapped_column(String(30), nullable=False)
    address_street: Mapped[str] = mapped_column(String(200), nullable=False)
    address_number: Mapped[str] = mapped_column(String(20), nullable=False)
    address_district: Mapped[str] = mapped_column(String(120), nullable=False)
    address_city: Mapped[str] = mapped_column(String(120), nullable=False)
    address_state: Mapped[str] = mapped_column(String(2), nullable=False)
    address_zip: Mapped[str] = mapped_column(String(15), nullable=False)
    ifms_bond: Mapped[IfmsBond] = mapped_column(Enum(IfmsBond, name="ifms_bond"), nullable=False)
    ifms_bond_other: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    campus: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    pi_author: Mapped["PIAuthor"] = relationship(back_populates="profile")


class AuthorDeclaration(Base):
    __tablename__ = "author_declarations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pi_author_id: Mapped[int] = mapped_column(
        ForeignKey("pi_authors.id", ondelete="CASCADE"), nullable=False
    )
    accepted_truth: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accepted_confidentiality: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    pi_author: Mapped["PIAuthor"] = relationship(back_populates="declarations")


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pi_author_id: Mapped[int] = mapped_column(
        ForeignKey("pi_authors.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(96), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    pi_author: Mapped["PIAuthor"] = relationship(back_populates="invitations")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pi_id: Mapped[int] = mapped_column(ForeignKey("pis.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[DocumentType] = mapped_column(Enum(DocumentType, name="document_type"), nullable=False)
    pdf_path: Mapped[str] = mapped_column(String(512), nullable=False)
    pi_author_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pi_authors.id", ondelete="SET NULL"), nullable=True
    )
    is_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    signed_file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    pi: Mapped["PI"] = relationship(back_populates="documents")
    pi_author: Mapped[Optional["PIAuthor"]] = relationship(back_populates="documents")


class AuthorDocument(Base):
    __tablename__ = "author_documents"
    __table_args__ = (
        UniqueConstraint("pi_author_id", "type", name="uq_author_documents_author_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pi_author_id: Mapped[int] = mapped_column(
        ForeignKey("pi_authors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[AuthorDocumentType] = mapped_column(
        Enum(AuthorDocumentType, name="author_document_type"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    pi_author: Mapped["PIAuthor"] = relationship(back_populates="personal_documents")


class AdminNotification(Base):
    __tablename__ = "admin_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pi_id: Mapped[int] = mapped_column(ForeignKey("pis.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"), nullable=False
    )
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    pi: Mapped["PI"] = relationship()
