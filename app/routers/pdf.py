from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import require_user
from app.models import (
    Document,
    PI,
    PIAuthor,
    User,
    UserRole,
)
from app.services.pdf_service import (
    all_authors_completed,
    build_zip_for_pi,
    generate_all_pdfs,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _can_view(user: User, pi: PI) -> bool:
    return user.role == UserRole.admin or pi.owner_id == user.id


def _load_pi(db: Session, pi_id: int) -> PI:
    pi = (
        db.query(PI)
        .options(
            selectinload(PI.authors).selectinload(PIAuthor.profile),
            selectinload(PI.documents),
            selectinload(PI.owner),
        )
        .filter(PI.id == pi_id)
        .first()
    )
    if not pi:
        raise HTTPException(status_code=404, detail="PI não encontrada")
    return pi


@router.post("/pis/{pi_id}/pdfs/generate", name="pi_pdf_generate")
async def pdf_generate(
    pi_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    pi = _load_pi(db, pi_id)
    if not _can_view(user, pi):
        raise HTTPException(status_code=403)
    if not all_authors_completed(pi):
        raise HTTPException(
            status_code=400,
            detail="Os PDFs só podem ser gerados quando todos os coautores concluírem.",
        )
    generate_all_pdfs(db, pi)
    db.commit()
    return RedirectResponse(url=f"/pis/{pi_id}", status_code=303)


@router.get("/pis/{pi_id}/documents/{doc_id}/download", name="pi_pdf_download")
async def pdf_download(
    pi_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    pi = _load_pi(db, pi_id)
    if not _can_view(user, pi):
        raise HTTPException(status_code=403)
    doc = db.get(Document, doc_id)
    if not doc or doc.pi_id != pi_id:
        raise HTTPException(status_code=404)
    if not os.path.exists(doc.pdf_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado em disco")
    filename = os.path.basename(doc.pdf_path)
    return FileResponse(doc.pdf_path, media_type="application/pdf", filename=filename)


@router.get("/pis/{pi_id}/documents.zip", name="pi_pdf_zip")
async def pdf_zip(
    pi_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    pi = _load_pi(db, pi_id)
    if not _can_view(user, pi):
        raise HTTPException(status_code=403)
    if not pi.documents:
        raise HTTPException(status_code=404, detail="Nenhum PDF gerado ainda")
    buf = build_zip_for_pi(pi)
    headers = {
        "Content-Disposition": f'attachment; filename="PI_{pi.id}_anexos.zip"'
    }
    return StreamingResponse(buf, media_type="application/zip", headers=headers)
