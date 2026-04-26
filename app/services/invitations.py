from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Invitation, PIAuthor
from app.services.email import EmailMessage, get_email_service
from app.templating import templates

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_token() -> str:
    return secrets.token_urlsafe(48)


def create_invitation(db: Session, pi_author: PIAuthor) -> Invitation:
    """Cria (ou substitui) o convite ativo para um PIAuthor."""
    for inv in pi_author.invitations:
        if not inv.used and inv.expires_at > _utcnow():
            inv.used = True
            inv.used_at = _utcnow()

    inv = Invitation(
        pi_author_id=pi_author.id,
        token=generate_token(),
        expires_at=_utcnow() + timedelta(hours=settings.invitation_expires_hours),
        used=False,
    )
    db.add(inv)
    db.flush()
    return inv


async def send_invitation_email(pi_author: PIAuthor, invitation: Invitation) -> None:
    """Renderiza HTML e envia email de convite para o coautor."""
    pi = pi_author.pi
    invite_url = f"{settings.app_base_url.rstrip('/')}/invite/{invitation.token}"

    html = templates.get_template("emails/invitation.html").render(
        pa=pi_author,
        pi=pi,
        invite_url=invite_url,
        expires_at=invitation.expires_at,
        percentage=float(pi_author.percentage),
        app_name=settings.app_name,
    )

    msg = EmailMessage(
        to=pi_author.email,
        subject=f"[{settings.app_name}] Convite como coautor - {pi.title}",
        html=html,
    )
    await get_email_service().send(msg)


def find_valid_invitation(db: Session, token: str) -> Invitation | None:
    inv = db.query(Invitation).filter(Invitation.token == token).first()
    if not inv:
        return None
    if inv.used:
        return None
    if inv.expires_at <= _utcnow():
        return None
    return inv


def mark_used(db: Session, invitation: Invitation) -> None:
    invitation.used = True
    invitation.used_at = _utcnow()
    db.flush()
