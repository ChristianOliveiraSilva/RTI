from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import get_db
from app.deps import require_admin
from app.models import (
    AdminNotification,
    Document,
    NotificationType,
    PI,
    PIAuthor,
    PIStatus,
    User,
)
from app.templating import IFMS_CAMPUSES, STATUS_LABELS, templates

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.get("", name="admin_panel")
async def admin_panel(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    campus_filter = request.query_params.get("campus", "").strip()
    status_filter = request.query_params.get("status", "").strip()

    q = (
        db.query(PI)
        .options(
            selectinload(PI.authors).selectinload(PIAuthor.profile),
            selectinload(PI.owner),
        )
        .filter(PI.deleted_at.is_(None))
    )

    if status_filter:
        q = q.filter(PI.status == status_filter)

    pis = q.order_by(PI.created_at.desc()).all()

    # Filter by campus (from primary author's profile)
    if campus_filter:
        filtered = []
        for pi in pis:
            primary = next((a for a in pi.authors if a.is_primary), None)
            if primary and primary.profile and primary.profile.campus == campus_filter:
                filtered.append(pi)
        pis = filtered

    # Notifications
    unread_count = db.query(AdminNotification).filter(AdminNotification.is_read == False).count()  # noqa: E712
    notifications = (
        db.query(AdminNotification)
        .order_by(AdminNotification.created_at.desc())
        .limit(50)
        .all()
    )

    return templates.TemplateResponse(
        request, "admin/panel.html",
        {
            "user": user,
            "pis": pis,
            "campuses": IFMS_CAMPUSES,
            "status_labels": STATUS_LABELS,
            "campus_filter": campus_filter,
            "status_filter": status_filter,
            "notifications": notifications,
            "unread_count": unread_count,
        },
    )


@router.post("/pis/{pi_id}/return-for-correction", name="admin_return_correction")
async def return_for_correction(
    pi_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    pi = db.query(PI).options(selectinload(PI.documents)).filter(PI.id == pi_id).first()
    if not pi:
        raise HTTPException(status_code=404)

    form = await request.form()
    notes = (form.get("admin_notes") or "").strip()

    pi.status = PIStatus.awaiting_corrections
    pi.admin_notes = notes
    pi.completed_at = None

    # Reset signed status on all documents
    for doc in pi.documents:
        doc.is_signed = False
        doc.signed_file_path = None

    db.commit()

    if request.headers.get("HX-Request"):
        return HTMLResponse(
            '<span class="badge badge-awaiting_corrections">Aguardando correções</span>'
        )
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/pis/{pi_id}/delete", name="admin_delete_pi")
async def delete_pi(
    pi_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    pi = db.query(PI).filter(PI.id == pi_id).first()
    if not pi:
        raise HTTPException(status_code=404)

    pi.deleted_at = _utcnow()
    db.commit()

    if request.headers.get("HX-Request"):
        return HTMLResponse("")
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/notifications/{notif_id}/read", name="admin_notif_read")
async def mark_notification_read(
    notif_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    notif = db.get(AdminNotification, notif_id)
    if not notif:
        raise HTTPException(status_code=404)
    notif.is_read = True
    db.commit()

    if request.headers.get("HX-Request"):
        return HTMLResponse("")
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/notifications/read-all", name="admin_notif_read_all")
async def mark_all_notifications_read(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    db.query(AdminNotification).filter(AdminNotification.is_read == False).update(  # noqa: E712
        {"is_read": True}
    )
    db.commit()

    if request.headers.get("HX-Request"):
        return HTMLResponse('<span class="muted">Todas lidas</span>')
    return RedirectResponse(url="/admin", status_code=303)
