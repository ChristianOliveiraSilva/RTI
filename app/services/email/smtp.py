from __future__ import annotations

import logging
import re
from email.message import EmailMessage as MIMEMessage

import aiosmtplib

from .base import EmailMessage, EmailService

logger = logging.getLogger(__name__)


def _strip_html(html: str) -> str:
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</\s*p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"[ \t]+", " ", text).strip()


class SMTPEmailService(EmailService):
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        default_from: str,
        default_from_name: str,
        use_tls: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.default_from = default_from
        self.default_from_name = default_from_name
        self.use_tls = use_tls

    async def send(self, message: EmailMessage) -> None:
        from_email = message.from_email or self.default_from
        from_name = message.from_name or self.default_from_name

        mime = MIMEMessage()
        mime["From"] = f"{from_name} <{from_email}>"
        mime["To"] = message.to
        mime["Subject"] = message.subject

        text_body = message.text or _strip_html(message.html)
        mime.set_content(text_body)
        mime.add_alternative(message.html, subtype="html")

        try:
            await aiosmtplib.send(
                mime,
                hostname=self.host,
                port=self.port,
                username=self.username or None,
                password=self.password or None,
                start_tls=self.use_tls,
                timeout=30,
            )
            logger.info("Email enviado via SMTP para %s (assunto=%s)", message.to, message.subject)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Falha ao enviar email para %s: %s", message.to, exc)
            raise
