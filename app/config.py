from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Registro de Propriedades Intelectuais - IFMS"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_base_url: str = "http://localhost:8000"

    secret_key: str = "change-me"
    session_cookie_name: str = "rpi_session"

    database_url: str = "postgresql+psycopg2://rpi:rpi_password@db:5432/rpi"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    admin_emails: str = ""

    mail_mailer: str = "smtp"
    mail_host: str = "sandbox.smtp.mailtrap.io"
    mail_port: int = 2525
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "no-reply@pi.local"
    mail_from_name: str = "Registro de Propriedades Intelectuais - IFMS"
    mail_use_tls: bool = True

    invitation_expires_hours: int = 48

    pdf_storage_dir: str = "/app/storage/pdfs"
    author_documents_storage_dir: str = "/app/storage/author_documents"
    pi_files_storage_dir: str = "/app/storage/pi_files"

    @property
    def admin_emails_list(self) -> List[str]:
        return [
            e.strip().lower()
            for e in self.admin_emails.split(",")
            if e.strip()
        ]

    @field_validator("secret_key")
    @classmethod
    def _validate_secret(cls, v: str) -> str:
        if not v or len(v) < 16:
            # Em produção isso deve ser um erro; em dev avisamos.
            return v or "dev-secret-please-change"
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
