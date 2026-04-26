from __future__ import annotations

import logging
from functools import lru_cache

from app.config import settings

from .base import EmailMessage, EmailService
from .smtp import SMTPEmailService

logger = logging.getLogger(__name__)


class LogEmailService(EmailService):
    """Fallback que apenas loga o email (útil para dev sem SMTP)."""

    async def send(self, message: EmailMessage) -> None:
        logger.warning(
            "LOG-EMAIL (mailer indisponível): to=%s subject=%s\n%s",
            message.to,
            message.subject,
            message.html,
        )


@lru_cache
def get_email_service() -> EmailService:
    mailer = (settings.mail_mailer or "smtp").lower()
    if mailer == "smtp":
        return SMTPEmailService(
            host=settings.mail_host,
            port=settings.mail_port,
            username=settings.mail_username,
            password=settings.mail_password,
            default_from=settings.mail_from,
            default_from_name=settings.mail_from_name,
            use_tls=settings.mail_use_tls,
        )
    if mailer in {"log", "null", "none"}:
        return LogEmailService()

    logger.warning("MAIL_MAILER=%s não reconhecido, caindo para LogEmailService", mailer)
    return LogEmailService()
