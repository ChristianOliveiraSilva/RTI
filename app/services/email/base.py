from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmailMessage:
    to: str
    subject: str
    html: str
    text: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None


class EmailService(ABC):
    """Interface comum para envio de emails (qualquer provider).

    Implementações concretas: SMTP, futuramente Sendgrid/SES/etc.
    """

    @abstractmethod
    async def send(self, message: EmailMessage) -> None:
        ...
