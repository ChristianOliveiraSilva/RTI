from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import get_db
from app.models import (
    AuthorDeclaration,
    AuthorDocument,
    AuthorDocumentType,
    AuthorProfile,
    IfmsBond,
    PIAuthor,
    PIAuthorStatus,
    PIStatus,
)
from app.services.author_documents_service import save_required_upload
from app.services.invitations import find_valid_invitation, mark_used
from app.templating import IFMS_BOND_LABELS, IFMS_CAMPUSES, templates

logger = logging.getLogger(__name__)
router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_inv(db: Session, token: str):
    inv = find_valid_invitation(db, token)
    if not inv:
        return None
    from app.models import PI
    pa = (
        db.query(PIAuthor)
        .options(
            selectinload(PIAuthor.profile),
            selectinload(PIAuthor.pi).selectinload(PI.authors).selectinload(PIAuthor.profile),
        )
        .filter(PIAuthor.id == inv.pi_author_id)
        .first()
    )
    if not pa:
        return None
    return inv, pa


@router.get("/invite/{token}", name="invite_form")
async def invite_form(token: str, request: Request, db: Session = Depends(get_db)):
    res = _load_inv(db, token)
    if not res:
        return templates.TemplateResponse(
            request, "invite/invalid.html", {}, status_code=410
        )
    inv, pa = res

    if pa.status == PIAuthorStatus.completed:
        return templates.TemplateResponse(
            request, "invite/done.html",
            {"pa": pa, "already": True},
        )

    profile = pa.profile

    return templates.TemplateResponse(
        request, "invite/form.html",
        {
            "token": token,
            "pa": pa,
            "pi": pa.pi,
            "profile": profile,
            "ifms_bonds": IFMS_BOND_LABELS,
            "ifms_campuses": IFMS_CAMPUSES,
            "errors": [],
            "expires_at": inv.expires_at,
        },
    )


@router.post("/invite/{token}", name="invite_submit")
async def invite_submit(token: str, request: Request, db: Session = Depends(get_db)):
    res = _load_inv(db, token)
    if not res:
        return templates.TemplateResponse(
            request, "invite/invalid.html", {}, status_code=410
        )
    inv, pa = res
    if pa.status == PIAuthorStatus.completed:
        return templates.TemplateResponse(
            request, "invite/done.html", {"pa": pa, "already": True}
        )

    form = await request.form()
    cpf_upload = form.get("cpf_file")
    rg_upload = form.get("rg_file")

    def f(key: str) -> str:
        return (form.get(key) or "").strip()

    fields = {
        "cpf": f("cpf"),
        "rg": f("rg"),
        "birth_date": f("birth_date"),
        "nationality": f("nationality"),
        "marital_status": f("marital_status"),
        "occupation": f("occupation"),
        "phone": f("phone") or None,
        "cellphone": f("cellphone"),
        "address_street": f("address_street"),
        "address_number": f("address_number"),
        "address_district": f("address_district"),
        "address_city": f("address_city"),
        "address_state": f("address_state").upper()[:2],
        "address_zip": f("address_zip"),
        "ifms_bond": f("ifms_bond"),
        "ifms_bond_other": f("ifms_bond_other"),
    }
    accepted_truth = form.get("accepted_truth") in ("on", "true", "1")
    accepted_conf = form.get("accepted_confidentiality") in ("on", "true", "1")

    errors = []
    required = [
        "cpf", "rg", "birth_date", "nationality", "marital_status",
        "occupation", "cellphone", "address_street", "address_number",
        "address_district", "address_city", "address_state", "address_zip",
        "ifms_bond",
    ]
    for k in required:
        if not fields[k]:
            errors.append(f"Campo obrigatório: {k}")
    if len(fields["address_state"]) != 2:
        errors.append("UF deve ter 2 caracteres.")
    try:
        ifms_bond_enum = IfmsBond(fields["ifms_bond"])
    except ValueError:
        ifms_bond_enum = None
        errors.append("Vínculo IFMS inválido.")

    bond_other_txt = (fields.get("ifms_bond_other") or "").strip()
    if ifms_bond_enum == IfmsBond.outros and not bond_other_txt:
        errors.append("Especifique o vínculo na opção Outros.")

    try:
        bd = datetime.strptime(fields["birth_date"], "%Y-%m-%d").date()
    except ValueError:
        bd = None
        errors.append("Data de nascimento inválida (use AAAA-MM-DD).")

    if not accepted_truth:
        errors.append("É preciso aceitar a declaração de veracidade (Anexo III).")
    if not accepted_conf:
        errors.append("É preciso aceitar o termo de confidencialidade (Anexo V).")

    if not getattr(cpf_upload, "filename", None):
        errors.append("Envie o documento do CPF (upload).")
    if not getattr(rg_upload, "filename", None):
        errors.append("Envie o documento do RG (upload).")

    existing = (
        db.query(AuthorDocument)
        .filter(
            AuthorDocument.pi_author_id == pa.id,
            AuthorDocument.type.in_([AuthorDocumentType.cpf, AuthorDocumentType.rg]),
        )
        .count()
    )
    if existing:
        errors.append("Documentos pessoais já foram enviados para este coautor (não é permitido reenviar).")

    if errors:
        return templates.TemplateResponse(
            request, "invite/form.html",
            {
                "token": token,
                "pa": pa,
                "pi": pa.pi,
                "profile": pa.profile,
                "ifms_bonds": IFMS_BOND_LABELS,
                "ifms_campuses": IFMS_CAMPUSES,
                "errors": errors,
                "expires_at": inv.expires_at,
                "submitted": fields,
                "accepted_truth": accepted_truth,
                "accepted_confidentiality": accepted_conf,
            },
            status_code=400,
        )

    profile = pa.profile
    values = {**fields, "ifms_bond": ifms_bond_enum, "birth_date": bd}
    values["ifms_bond_other"] = bond_other_txt if ifms_bond_enum == IfmsBond.outros else None

    # Determine campus for coauthor based on institution and primary author's campus
    if pa.institution == "ifms":
        primary_author = next((a for a in pa.pi.authors if a.is_primary), None)
        if primary_author and primary_author.profile:
            values["campus"] = primary_author.profile.campus
        else:
            values["campus"] = None
    else:
        values["campus"] = bond_other_txt if ifms_bond_enum == IfmsBond.outros else None

    if profile is None:
        profile = AuthorProfile(pi_author_id=pa.id, **values)
        db.add(profile)
    else:
        for k, v in values.items():
            setattr(profile, k, v)

    try:
        base_dir = os.path.join(
            settings.author_documents_storage_dir,
            f"pi_{pa.pi_id}",
            f"author_{pa.id}",
        )
        cpf_path, cpf_name, cpf_ct = await save_required_upload(
            cpf_upload,
            os.path.join(base_dir, "cpf"),
            max_bytes=10 * 1024 * 1024,
        )
        rg_path, rg_name, rg_ct = await save_required_upload(
            rg_upload,
            os.path.join(base_dir, "rg"),
            max_bytes=10 * 1024 * 1024,
        )
        db.add(
            AuthorDocument(
                pi_author_id=pa.id,
                type=AuthorDocumentType.cpf,
                file_path=cpf_path,
                original_filename=cpf_name,
                content_type=cpf_ct or None,
            )
        )
        db.add(
            AuthorDocument(
                pi_author_id=pa.id,
                type=AuthorDocumentType.rg,
                file_path=rg_path,
                original_filename=rg_name,
                content_type=rg_ct or None,
            )
        )
        db.flush()
    except HTTPException:
        db.rollback()
        raise

    db.add(
        AuthorDeclaration(
            pi_author_id=pa.id,
            accepted_truth=True,
            accepted_confidentiality=True,
        )
    )

    pa.status = PIAuthorStatus.completed
    pa.completed_at = _utcnow()

    mark_used(db, inv)

    pi = pa.pi
    if all(p.status == PIAuthorStatus.completed for p in pi.authors):
        pi.status = PIStatus.awaiting_signatures

    db.commit()

    return templates.TemplateResponse(
        request, "invite/done.html", {"pa": pa, "already": False},
    )
