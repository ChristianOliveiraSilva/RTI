from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import require_user
from app.models import (
    AuthorDeclaration,
    AuthorDocument,
    AuthorDocumentType,
    AuthorProfile,
    IfmsBond,
    PI,
    PIAuthor,
    PIAuthorStatus,
    PIStatus,
    PIType,
    User,
    UserRole,
)
from app.config import settings
from app.services.author_documents_service import save_required_upload
from app.services.invitations import create_invitation, send_invitation_email
from app.templating import IFMS_BOND_LABELS, PI_TYPE_LABELS, templates

logger = logging.getLogger(__name__)
router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _can_view(user: User, pi: PI) -> bool:
    return user.role == UserRole.admin or pi.owner_id == user.id


def _empty_primary() -> dict:
    return {
        "cpf": "",
        "rg": "",
        "birth_date": "",
        "nationality": "",
        "marital_status": "",
        "occupation": "",
        "phone": "",
        "cellphone": "",
        "address_street": "",
        "address_number": "",
        "address_district": "",
        "address_city": "",
        "address_state": "",
        "address_zip": "",
        "ifms_bond": "",
        "ifms_bond_other": "",
    }


@router.get("/pis/_coauthor_row", name="pi_coauthor_row", response_class=HTMLResponse)
async def coauthor_row(request: Request, user: User = Depends(require_user)):
    return templates.TemplateResponse(
        request, "pi/_coauthor_row.html",
        {"c": {"name": "", "email": "", "percentage": ""}},
    )


@router.get("/pis/new", name="pi_new")
async def pi_new_form(request: Request, user: User = Depends(require_user)):
    return templates.TemplateResponse(
        request, "pi/new.html",
        {
            "user": user,
            "pi_types": PI_TYPE_LABELS,
            "ifms_bonds": IFMS_BOND_LABELS,
            "errors": [],
            "form": {
                "title": "",
                "type": "software",
                "description": "",
                "programming_language": "",
                "creation_date": "",
                "publication_date": "",
                "application_field": "",
                "program_type": "",
                "source_hash": "",
                "is_derived": False,
                "derived_title": "",
                "derived_registration": "",
                "has_partner": False,
                "partner_name": "",
                "partner_cnpj": "",
                "partner_contact": "",
                "partner_percentage": "",
                "primary_percentage": "",
            },
            "primary": _empty_primary(),
            "coauthors": [],
            "accepted_truth": False,
            "accepted_confidentiality": False,
        },
    )


@router.post("/pis", name="pi_create")
async def pi_create(
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    form = await request.form()

    # ---- Dados da Propriedade Intelectual ----
    title = (form.get("title") or "").strip()
    pi_type = (form.get("type") or "").strip()
    description = (form.get("description") or "").strip()

    # ---- Dados do Programa (Anexo I) ----
    programming_language = (form.get("programming_language") or "").strip()
    creation_date_raw = (form.get("creation_date") or "").strip()
    publication_date_raw = (form.get("publication_date") or "").strip()
    application_field = (form.get("application_field") or "").strip()
    program_type = (form.get("program_type") or "").strip()
    source_hash = (form.get("source_hash") or "").strip()
    is_derived = form.get("is_derived") in ("on", "true", "1")
    derived_title = (form.get("derived_title") or "").strip()
    derived_registration = (form.get("derived_registration") or "").strip()

    has_partner = form.get("has_partner") in ("on", "true", "1")
    partner_name = (form.get("partner_name") or "").strip() or None
    partner_cnpj = (form.get("partner_cnpj") or "").strip() or None
    partner_contact = (form.get("partner_contact") or "").strip() or None
    partner_percentage_raw = (form.get("partner_percentage") or "").strip()
    primary_percentage = (form.get("primary_percentage") or "").strip()

    # ---- Coautores ----
    coauthor_names = form.getlist("coauthor_name")
    coauthor_emails = form.getlist("coauthor_email")
    coauthor_percentages = form.getlist("coauthor_percentage")
    coauthor_institutions = form.getlist("coauthor_institution")

    # ---- Profile do autor principal ----
    primary = {
        "cpf": (form.get("cpf") or "").strip(),
        "rg": (form.get("rg") or "").strip(),
        "birth_date": (form.get("birth_date") or "").strip(),
        "nationality": (form.get("nationality") or "").strip(),
        "marital_status": (form.get("marital_status") or "").strip(),
        "occupation": (form.get("occupation") or "").strip(),
        "phone": (form.get("phone") or "").strip(),
        "cellphone": (form.get("cellphone") or "").strip(),
        "address_street": (form.get("address_street") or "").strip(),
        "address_number": (form.get("address_number") or "").strip(),
        "address_district": (form.get("address_district") or "").strip(),
        "address_city": (form.get("address_city") or "").strip(),
        "address_state": (form.get("address_state") or "").strip().upper()[:2],
        "address_zip": (form.get("address_zip") or "").strip(),
        "ifms_bond": (form.get("ifms_bond") or "").strip(),
        "ifms_bond_other": (form.get("ifms_bond_other") or "").strip(),
    }
    accepted_truth = form.get("accepted_truth") in ("on", "true", "1")
    accepted_conf = form.get("accepted_confidentiality") in ("on", "true", "1")

    errors: List[str] = []

    cpf_upload = form.get("cpf_file")
    rg_upload = form.get("rg_file")

    # ---- Validações da PI ----
    if not title:
        errors.append("Informe o título da Propriedade Intelectual.")
    try:
        pi_type_enum = PIType(pi_type)
    except ValueError:
        pi_type_enum = PIType.outro
        errors.append("Tipo de Propriedade Intelectual inválido.")

    if not programming_language:
        errors.append("Informe a linguagem de programação.")
    if not application_field:
        errors.append("Informe o campo de aplicação.")
    if not program_type:
        errors.append("Informe o tipo de programa.")
    if not source_hash:
        errors.append("Informe o hash do código-fonte.")

    creation_date_val = None
    if creation_date_raw:
        try:
            creation_date_val = datetime.strptime(creation_date_raw, "%Y-%m-%d").date()
        except ValueError:
            errors.append("Data de criação inválida.")

    publication_date_val = None
    if publication_date_raw:
        try:
            publication_date_val = datetime.strptime(publication_date_raw, "%Y-%m-%d").date()
        except ValueError:
            errors.append("Data de publicação inválida.")

    if not creation_date_raw and not publication_date_raw:
        errors.append("Informe a data de criação ou a data de publicação.")

    if has_partner and not partner_name:
        errors.append("Informe o nome da instituição parceira.")

    partner_pct: float | None = None
    if has_partner:
        try:
            partner_pct = float(partner_percentage_raw.replace(",", "."))
        except ValueError:
            partner_pct = None
            errors.append("Informe a porcentagem de titularidade do parceiro.")

    try:
        primary_pct = float(primary_percentage.replace(",", "."))
    except ValueError:
        primary_pct = 0.0
        errors.append("Sua porcentagem (autor principal) é inválida.")

    # ---- Validações do profile do autor principal ----
    required_profile = [
        "cpf", "rg", "birth_date", "nationality", "marital_status", "occupation",
        "cellphone", "address_street", "address_number", "address_district",
        "address_city", "address_state", "address_zip", "ifms_bond",
    ]
    for k in required_profile:
        if not primary[k]:
            errors.append(f"Campo obrigatório do autor principal: {k}")

    if primary["address_state"] and len(primary["address_state"]) != 2:
        errors.append("UF do autor principal deve ter 2 caracteres.")

    primary_bond = None
    if primary["ifms_bond"]:
        try:
            primary_bond = IfmsBond(primary["ifms_bond"])
        except ValueError:
            errors.append("Vínculo IFMS do autor principal inválido.")

    if primary_bond == IfmsBond.outros and not primary["ifms_bond_other"]:
        errors.append("Especifique o vínculo na opção Outros.")

    primary_bd = None
    if primary["birth_date"]:
        try:
            primary_bd = datetime.strptime(primary["birth_date"], "%Y-%m-%d").date()
        except ValueError:
            errors.append("Data de nascimento do autor principal inválida (use AAAA-MM-DD).")

    if not accepted_truth:
        errors.append("É preciso aceitar a declaração de veracidade (Anexo III).")
    if not accepted_conf:
        errors.append("É preciso aceitar o termo de confidencialidade (Anexo V).")

    if not getattr(cpf_upload, "filename", None):
        errors.append("Envie o documento do CPF (upload).")
    if not getattr(rg_upload, "filename", None):
        errors.append("Envie o documento do RG (upload).")

    # ---- Validações dos coautores ----
    coauthors_clean = []
    seen_emails = {user.email.lower()}
    total = primary_pct
    for idx, (nm, em, pc) in enumerate(zip(coauthor_names, coauthor_emails, coauthor_percentages)):
        nm = (nm or "").strip()
        em = (em or "").strip().lower()
        pc = (pc or "").strip().replace(",", ".")
        inst = (coauthor_institutions[idx] if idx < len(coauthor_institutions) else "ifms").strip() or "ifms"
        if not nm and not em and not pc:
            continue
        if not nm or not em or not pc:
            errors.append("Coautor com dados incompletos.")
            continue
        if em in seen_emails:
            errors.append(f"Email duplicado: {em}")
            continue
        try:
            pcv = float(pc)
        except ValueError:
            errors.append(f"Porcentagem inválida para {em}.")
            continue
        seen_emails.add(em)
        total += pcv
        coauthors_clean.append({"name": nm, "email": em, "percentage": pcv, "institution": inst})

    if abs(total - 100.0) > 0.01:
        errors.append(f"A soma das porcentagens deve ser 100% (atual: {total:g}%).")

    # ---- Re-render em caso de erro ----
    if errors:
        return templates.TemplateResponse(
            request, "pi/new.html",
            {
                "user": user,
                "pi_types": PI_TYPE_LABELS,
                "ifms_bonds": IFMS_BOND_LABELS,
                "errors": errors,
                "form": {
                    "title": title,
                    "type": pi_type,
                    "description": description,
                    "programming_language": programming_language,
                    "creation_date": creation_date_raw,
                    "publication_date": publication_date_raw,
                    "application_field": application_field,
                    "program_type": program_type,
                    "source_hash": source_hash,
                    "is_derived": is_derived,
                    "derived_title": derived_title,
                    "derived_registration": derived_registration,
                    "has_partner": has_partner,
                    "partner_name": partner_name or "",
                    "partner_cnpj": partner_cnpj or "",
                    "partner_contact": partner_contact or "",
                    "partner_percentage": partner_percentage_raw,
                    "primary_percentage": primary_percentage,
                },
                "primary": primary,
                "accepted_truth": accepted_truth,
                "accepted_confidentiality": accepted_conf,
                "coauthors": [
                    {"name": c["name"], "email": c["email"], "percentage": c["percentage"], "institution": c["institution"]}
                    for c in coauthors_clean
                ] or [
                    {"name": n, "email": e, "percentage": p, "institution": coauthor_institutions[i] if i < len(coauthor_institutions) else "ifms"}
                    for i, (n, e, p) in enumerate(zip(coauthor_names, coauthor_emails, coauthor_percentages))
                    if (n or e or p)
                ],
            },
            status_code=400,
        )

    # ---- Persistência ----
    pi = PI(
        title=title,
        type=pi_type_enum,
        description=description or None,
        programming_language=programming_language or None,
        creation_date=creation_date_val,
        publication_date=publication_date_val,
        application_field=application_field or None,
        program_type=program_type or None,
        source_hash=source_hash or None,
        is_derived=is_derived,
        derived_title=derived_title or None if is_derived else None,
        derived_registration=derived_registration or None if is_derived else None,
        has_partner=has_partner,
        partner_name=partner_name if has_partner else None,
        partner_cnpj=partner_cnpj if has_partner else None,
        partner_contact=partner_contact if has_partner else None,
        partner_percentage=partner_pct if has_partner else None,
        owner_id=user.id,
        status=PIStatus.awaiting_authors,
    )
    db.add(pi)
    db.flush()

    # Autor principal já preenchido => completed e sem convite
    primary_pa = PIAuthor(
        pi_id=pi.id,
        name=user.name,
        email=user.email.lower(),
        percentage=primary_pct,
        is_primary=True,
        institution="ifms",
        status=PIAuthorStatus.completed,
        completed_at=_utcnow(),
    )
    db.add(primary_pa)
    db.flush()

    try:
        base_dir = os.path.join(
            settings.author_documents_storage_dir,
            f"pi_{pi.id}",
            f"author_{primary_pa.id}",
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
                pi_author_id=primary_pa.id,
                type=AuthorDocumentType.cpf,
                file_path=cpf_path,
                original_filename=cpf_name,
                content_type=cpf_ct or None,
            )
        )
        db.add(
            AuthorDocument(
                pi_author_id=primary_pa.id,
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

    profile_values = {
        "cpf": primary["cpf"],
        "rg": primary["rg"],
        "birth_date": primary_bd,
        "nationality": primary["nationality"],
        "marital_status": primary["marital_status"],
        "occupation": primary["occupation"],
        "phone": primary["phone"] or None,
        "cellphone": primary["cellphone"],
        "address_street": primary["address_street"],
        "address_number": primary["address_number"],
        "address_district": primary["address_district"],
        "address_city": primary["address_city"],
        "address_state": primary["address_state"],
        "address_zip": primary["address_zip"],
        "ifms_bond": primary_bond,
        "ifms_bond_other": primary["ifms_bond_other"] if primary_bond == IfmsBond.outros else None,
    }
    db.add(AuthorProfile(pi_author_id=primary_pa.id, **profile_values))
    db.add(
        AuthorDeclaration(
            pi_author_id=primary_pa.id,
            accepted_truth=True,
            accepted_confidentiality=True,
        )
    )

    # Coautores: pendentes + convite
    pa_to_email: list[PIAuthor] = []
    for c in coauthors_clean:
        pa = PIAuthor(
            pi_id=pi.id,
            name=c["name"],
            email=c["email"],
            percentage=c["percentage"],
            is_primary=False,
            institution=c["institution"],
            status=PIAuthorStatus.pending,
        )
        db.add(pa)
        db.flush()
        pa_to_email.append(pa)

    invs_to_send: list[tuple[int, str]] = []
    for pa in pa_to_email:
        inv = create_invitation(db, pa)
        invs_to_send.append((pa.id, inv.token))

    # Sem coautores? Propriedade Intelectual já fica completed.
    if not pa_to_email:
        pi.status = PIStatus.completed
        pi.completed_at = _utcnow()

    db.commit()

    async def _send_all():
        from app.database import SessionLocal
        from app.models import Invitation as _Inv, PIAuthor as _PIA
        with SessionLocal() as s:
            for pa_id, token in invs_to_send:
                inv = s.query(_Inv).filter(_Inv.token == token).first()
                pa_db = s.query(_PIA).options(selectinload(_PIA.pi)).get(pa_id)
                if inv and pa_db:
                    try:
                        await send_invitation_email(pa_db, inv)
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("Falha ao enviar convite: %s", exc)

    if invs_to_send:
        background.add_task(_send_all)

    return RedirectResponse(url=f"/pis/{pi.id}", status_code=303)


@router.get("/pis/{pi_id}", name="pi_show")
async def pi_show(
    pi_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    pi = (
        db.query(PI)
        .options(
            selectinload(PI.authors).selectinload(PIAuthor.invitations),
            selectinload(PI.authors).selectinload(PIAuthor.personal_documents),
            selectinload(PI.documents),
            selectinload(PI.owner),
        )
        .filter(PI.id == pi_id)
        .first()
    )
    if not pi:
        raise HTTPException(status_code=404, detail="Propriedade Intelectual não encontrada")
    if not _can_view(user, pi):
        raise HTTPException(status_code=403, detail="Sem permissão")

    all_done = all(pa.status == PIAuthorStatus.completed for pa in pi.authors)

    return templates.TemplateResponse(
        request, "pi/show.html",
        {
            "user": user,
            "pi": pi,
            "all_done": all_done,
            "is_owner": pi.owner_id == user.id,
            "is_admin": user.role == UserRole.admin,
        },
    )


@router.get(
    "/pis/{pi_id}/authors/{pa_id}/personal-docs/{doc_type}/download",
    name="pi_author_personal_doc_download",
)
async def author_personal_doc_download(
    pi_id: int,
    pa_id: int,
    doc_type: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    pi = db.query(PI).filter(PI.id == pi_id).first()
    if not pi:
        raise HTTPException(status_code=404, detail="Propriedade Intelectual não encontrada")
    if not _can_view(user, pi):
        raise HTTPException(status_code=403, detail="Sem permissão")

    pa = db.query(PIAuthor).filter(PIAuthor.id == pa_id, PIAuthor.pi_id == pi_id).first()
    if not pa:
        raise HTTPException(status_code=404, detail="Autor não encontrado")

    try:
        dtype = AuthorDocumentType(doc_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Tipo de documento inválido")

    doc = (
        db.query(AuthorDocument)
        .filter(AuthorDocument.pi_author_id == pa_id, AuthorDocument.type == dtype)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado em disco")

    filename = os.path.basename(doc.file_path)
    media_type = doc.content_type or "application/octet-stream"
    return FileResponse(doc.file_path, media_type=media_type, filename=filename)


@router.post("/pis/{pi_id}/authors/{pa_id}/resend", name="pi_resend_invite")
async def pi_resend_invite(
    pi_id: int,
    pa_id: int,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    pi = db.query(PI).filter(PI.id == pi_id).first()
    if not pi:
        raise HTTPException(status_code=404)
    if not _can_view(user, pi):
        raise HTTPException(status_code=403)
    pa = (
        db.query(PIAuthor)
        .options(selectinload(PIAuthor.pi))
        .filter(PIAuthor.id == pa_id, PIAuthor.pi_id == pi_id)
        .first()
    )
    if not pa:
        raise HTTPException(status_code=404)
    if pa.status == PIAuthorStatus.completed:
        raise HTTPException(status_code=400, detail="Coautor já concluído")

    inv = create_invitation(db, pa)
    db.commit()

    inv_id = inv.id
    pa_id_local = pa.id

    async def _do_send():
        from app.database import SessionLocal
        from app.models import Invitation as _Inv, PIAuthor as _PIA
        with SessionLocal() as s:
            inv2 = s.query(_Inv).filter(_Inv.id == inv_id).first()
            pa2 = s.query(_PIA).options(selectinload(_PIA.pi)).get(pa_id_local)
            try:
                await send_invitation_email(pa2, inv2)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Reenvio falhou: %s", exc)

    background.add_task(_do_send)

    if request.headers.get("HX-Request"):
        return HTMLResponse(
            '<button type="button" class="btn btn-ghost btn-sm" disabled>'
            "Convite enviado"
            "</button>"
        )
    return RedirectResponse(url=f"/pis/{pi_id}", status_code=303)
