from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models import PI, UserRole
from app.templating import templates

router = APIRouter()


@router.get("/", include_in_schema=False)
async def root(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/dashboard", name="dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    q = db.query(PI).options(
        selectinload(PI.authors),
        selectinload(PI.documents),
    )
    if user.role != UserRole.admin:
        q = q.filter(PI.owner_id == user.id)
    pis = q.order_by(PI.created_at.desc()).all()

    return templates.TemplateResponse(
        request, "dashboard.html",
        {
            "user": user,
            "pis": pis,
            "is_admin": user.role == UserRole.admin,
        },
    )
