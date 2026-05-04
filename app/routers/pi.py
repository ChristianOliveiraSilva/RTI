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
    AdminNotification,
    AuthorDeclaration,
    AuthorDocument,
    AuthorDocumentType,
    AuthorProfile,
    Document,
    IfmsBond,
    NotificationType,
    PI,
    PIAuthor,
    PIAuthorStatus,
    PIStatus,
    PIType,
    User,
    UserRole,
)
from app.config import settings
from app.services.author_documents_service import save_flexible_upload, save_required_upload
from app.services.invitations import create_invitation, send_invitation_email
from app.templating import IFMS_BOND_LABELS, IFMS_CAMPUSES, PI_TYPE_LABELS, templates

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
        "campus": "",
    }


@router.get("/pis/_coauthor_row", name="pi_coauthor_row", response_class=HTMLResponse)
async def coauthor_row(request: Request, user: User = Depends(require_user)):
    return templates.TemplateResponse(
        request, "pi/_coauthor_row.html",
        {"c": {"name": "", "email": "", "percentage": ""}},
    )


def _empty_form() -> dict:
    return {
        "title": "",
        "type": "software",
        "description": "",
        # Software fields
        "programming_language": "",
        "creation_date": "",
        "publication_date": "",
        "application_field": "",
        "program_type": "",
        "source_hash": "",
        "is_derived": False,
        "derived_title": "",
        "derived_registration": "",
        # Marca fields
        "marca_nome": "",
        "marca_tipo": "",
        "marca_idioma_estrangeiro": False,
        "marca_termo_estrangeiro": "",
        "marca_traducao": "",
        "marca_termos_colidencia": "",
        "marca_nice": "",
        "marca_viena": "",
        "marca_protecao_indicada": False,
        "marca_protecao_justificativa": "",
        # Partner
        "has_partner": False,
        "partner_name": "",
        "partner_cnpj": "",
        "partner_contact": "",
        "primary_percentage": "",
    }


@router.get("/pis/new", name="pi_new")
async def pi_new_form(request: Request, user: User = Depends(require_user)):
    return templates.TemplateResponse(
        request, "pi/new.html",
        {
            "user": user,
            "pi_types": PI_TYPE_LABELS,
            "ifms_bonds": IFMS_BOND_LABELS,
            "ifms_campuses": IFMS_CAMPUSES,
            "errors": [],
            "form": _empty_form(),
            "primary": _empty_primary(),
            "coauthors": [],
            "accepted_truth": False,
            "accepted_confidentiality": False,
            "edit_mode": False,
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

    # ---- Dados do Programa (Anexo I) - software only ----
    programming_language = (form.get("programming_language") or "").strip()
    creation_date_raw = (form.get("creation_date") or "").strip()
    publication_date_raw = (form.get("publication_date") or "").strip()
    application_field = (form.get("application_field") or "").strip()
    program_type = (form.get("program_type") or "").strip()
    source_hash = (form.get("source_hash") or "").strip()
    is_derived = form.get("is_derived") in ("on", "true", "1")
    derived_title = (form.get("derived_title") or "").strip()
    derived_registration = (form.get("derived_registration") or "").strip()

    # ---- Marca fields ----
    marca_nome = (form.get("marca_nome") or "").strip()
    marca_tipo = (form.get("marca_tipo") or "").strip()
    marca_idioma_estrangeiro = form.get("marca_idioma_estrangeiro") in ("on", "true", "1")
    marca_termo_estrangeiro = (form.get("marca_termo_estrangeiro") or "").strip()
    marca_traducao = (form.get("marca_traducao") or "").strip()
    marca_termos_colidencia = (form.get("marca_termos_colidencia") or "").strip()
    marca_nice = (form.get("marca_nice") or "").strip()
    marca_viena = (form.get("marca_viena") or "").strip()
    marca_protecao_indicada = form.get("marca_protecao_indicada") in ("on", "true", "1")
    marca_protecao_justificativa = (form.get("marca_protecao_justificativa") or "").strip()
    marca_imagem_upload = form.get("marca_imagem_file")

    # ---- Software uploads ----
    video_upload = form.get("video_file")
    source_code_upload = form.get("source_code_file")

    has_partner = form.get("has_partner") in ("on", "true", "1")
    partner_name = (form.get("partner_name") or "").strip() or None
    partner_cnpj = (form.get("partner_cnpj") or "").strip() or None
    partner_contact = (form.get("partner_contact") or "").strip() or None
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
        "campus": (form.get("campus") or "").strip(),
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

    # ---- Validações condicionais por tipo ----
    creation_date_val = None
    publication_date_val = None

    if pi_type_enum == PIType.software:
        if not programming_language:
            errors.append("Informe a linguagem de programação.")
        if not application_field:
            errors.append("Informe o campo de aplicação.")
        if not program_type:
            errors.append("Informe o tipo de programa.")
        if not source_hash:
            errors.append("Informe o hash do código-fonte.")
        if creation_date_raw:
            try:
                creation_date_val = datetime.strptime(creation_date_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Data de criação inválida.")
        if publication_date_raw:
            try:
                publication_date_val = datetime.strptime(publication_date_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Data de publicação inválida.")
        if not creation_date_raw and not publication_date_raw:
            errors.append("Informe a data de criação ou a data de publicação.")

    if pi_type_enum == PIType.marca:
        if not marca_nome:
            errors.append("Informe o nome da marca.")
        if not marca_tipo:
            errors.append("Selecione o tipo de marca.")

    if has_partner and not partner_name:
        errors.append("Informe o nome da instituição parceira.")

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

    if primary_bond and primary_bond != IfmsBond.outros and not primary["campus"]:
        errors.append("Selecione o campus do IFMS.")

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

    partner_pct = sum(
        c["percentage"] for c in coauthors_clean if c.get("institution") == "partner"
    )
    if has_partner and partner_pct <= 0:
        errors.append(
            "Com parceria, inclua pelo menos um coautor com instituição "
            '"Instituição parceira" e distribua as porcentagens entre IFMS e parceiro.'
        )
    if not has_partner and partner_pct > 0:
        errors.append(
            "Algum coautor está vinculado à instituição parceira; marque "
            '"Possui instituição parceira" ou altere todos os coautores para IFMS.'
        )

    # ---- Re-render em caso de erro ----
    if errors:
        return templates.TemplateResponse(
            request, "pi/new.html",
            {
                "user": user,
                "pi_types": PI_TYPE_LABELS,
                "ifms_bonds": IFMS_BOND_LABELS,
                "ifms_campuses": IFMS_CAMPUSES,
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
                    "marca_nome": marca_nome,
                    "marca_tipo": marca_tipo,
                    "marca_idioma_estrangeiro": marca_idioma_estrangeiro,
                    "marca_termo_estrangeiro": marca_termo_estrangeiro,
                    "marca_traducao": marca_traducao,
                    "marca_termos_colidencia": marca_termos_colidencia,
                    "marca_nice": marca_nice,
                    "marca_viena": marca_viena,
                    "marca_protecao_indicada": marca_protecao_indicada,
                    "marca_protecao_justificativa": marca_protecao_justificativa,
                    "has_partner": has_partner,
                    "partner_name": partner_name or "",
                    "partner_cnpj": partner_cnpj or "",
                    "partner_contact": partner_contact or "",
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
                "edit_mode": False,
            },
            status_code=400,
        )

    # ---- Persistência ----
    pi = PI(
        title=title,
        type=pi_type_enum,
        description=description or None,
        has_partner=has_partner,
        partner_name=partner_name if has_partner else None,
        partner_cnpj=partner_cnpj if has_partner else None,
        partner_contact=partner_contact if has_partner else None,
        partner_percentage=partner_pct if has_partner else None,
        owner_id=user.id,
        status=PIStatus.awaiting_authors,
    )

    # Software-specific fields
    if pi_type_enum == PIType.software:
        pi.programming_language = programming_language or None
        pi.creation_date = creation_date_val
        pi.publication_date = publication_date_val
        pi.application_field = application_field or None
        pi.program_type = program_type or None
        pi.source_hash = source_hash or None
        pi.is_derived = is_derived
        pi.derived_title = derived_title or None if is_derived else None
        pi.derived_registration = derived_registration or None if is_derived else None

    # Marca-specific fields
    if pi_type_enum == PIType.marca:
        pi.marca_nome = marca_nome or None
        pi.marca_tipo = marca_tipo or None
        pi.marca_idioma_estrangeiro = marca_idioma_estrangeiro
        pi.marca_termo_estrangeiro = marca_termo_estrangeiro or None
        pi.marca_traducao = marca_traducao or None
        pi.marca_termos_colidencia = marca_termos_colidencia or None
        pi.marca_nice = marca_nice or None
        pi.marca_viena = marca_viena or None
        pi.marca_protecao_indicada = marca_protecao_indicada
        pi.marca_protecao_justificativa = marca_protecao_justificativa or None

    db.add(pi)
    db.flush()

    # ---- Software uploads (video + source code) ----
    if pi_type_enum == PIType.software:
        pi_files_dir = os.path.join(settings.pi_files_storage_dir, f"pi_{pi.id}")
        video_result = await save_flexible_upload(
            video_upload, os.path.join(pi_files_dir, "video", "video"),
            max_bytes=200 * 1024 * 1024,
            allowed_exts={"mp4", "avi", "mkv", "pdf", "docx", "zip", "rar"},
        )
        if video_result:
            pi.video_path, pi.video_original_filename, _ = video_result

        sc_result = await save_flexible_upload(
            source_code_upload, os.path.join(pi_files_dir, "source_code", "source"),
            max_bytes=200 * 1024 * 1024,
            allowed_exts={"zip", "rar", "7z", "tar", "gz"},
        )
        if sc_result:
            pi.source_code_path, pi.source_code_original_filename, _ = sc_result

    # ---- Marca image upload ----
    if pi_type_enum == PIType.marca:
        pi_files_dir = os.path.join(settings.pi_files_storage_dir, f"pi_{pi.id}")
        img_result = await save_flexible_upload(
            marca_imagem_upload, os.path.join(pi_files_dir, "marca", "imagem"),
            max_bytes=10 * 1024 * 1024,
            allowed_exts={"jpg", "jpeg", "png", "gif", "svg", "webp"},
        )
        if img_result:
            pi.marca_imagem_path, pi.marca_imagem_original_filename, _ = img_result

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

    # Determine campus for the primary author
    primary_campus = primary["campus"] if primary_bond != IfmsBond.outros else None

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
        "campus": primary_campus,
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

    # Without coauthors the PI goes directly to awaiting_signatures
    if not pa_to_email:
        pi.status = PIStatus.awaiting_signatures

    # Admin notification
    db.add(AdminNotification(
        pi_id=pi.id,
        type=NotificationType.new_pi,
        message=f"Nova PI cadastrada: {pi.title}",
    ))

    # Capture data for background tasks before commit closes session
    _pi_id = pi.id
    _pi_title = pi.title
    _pi_type_val = pi.type.value
    _owner_name = user.name
    _owner_email = user.email

    db.commit()

    async def _notify_admins():
        from app.services.email import EmailMessage, get_email_service
        for admin_email in settings.admin_emails_list:
            try:
                html = templates.get_template("emails/admin_new_pi.html").render(
                    pi_title=_pi_title, pi_type=_pi_type_val, pi_id=_pi_id,
                    owner_name=_owner_name, owner_email=_owner_email,
                    app_name=settings.app_name, base_url=settings.app_base_url,
                )
                await get_email_service().send(EmailMessage(
                    to=admin_email,
                    subject=f"[{settings.app_name}] Nova PI cadastrada: {_pi_title}",
                    html=html,
                ))
            except Exception as exc:  # noqa: BLE001
                logger.exception("Falha ao notificar admin %s: %s", admin_email, exc)

    background.add_task(_notify_admins)

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

    return RedirectResponse(url=f"/pis/{_pi_id}", status_code=303)


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

    correcao_dup = request.query_params.get("correcao_ja_enviada") == "1"

    return templates.TemplateResponse(
        request, "pi/show.html",
        {
            "user": user,
            "pi": pi,
            "all_done": all_done,
            "is_owner": pi.owner_id == user.id,
            "is_admin": user.role == UserRole.admin,
            "correcao_ja_enviada": correcao_dup,
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


@router.get("/pis/{pi_id}/video/download", name="pi_video_download")
async def pi_video_download(
    pi_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    pi = db.query(PI).filter(PI.id == pi_id).first()
    if not pi:
        raise HTTPException(status_code=404)
    if not _can_view(user, pi):
        raise HTTPException(status_code=403)
    if not pi.video_path or not os.path.exists(pi.video_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(
        pi.video_path,
        media_type="application/octet-stream",
        filename=pi.video_original_filename or os.path.basename(pi.video_path),
    )


@router.get("/pis/{pi_id}/source-code/download", name="pi_source_code_download")
async def pi_source_code_download(
    pi_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    pi = db.query(PI).filter(PI.id == pi_id).first()
    if not pi:
        raise HTTPException(status_code=404)
    if not _can_view(user, pi):
        raise HTTPException(status_code=403)
    if not pi.source_code_path or not os.path.exists(pi.source_code_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(
        pi.source_code_path,
        media_type="application/zip",
        filename=pi.source_code_original_filename or os.path.basename(pi.source_code_path),
    )


@router.get("/pis/{pi_id}/marca-imagem/download", name="pi_marca_imagem_download")
async def pi_marca_imagem_download(
    pi_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    pi = db.query(PI).filter(PI.id == pi_id).first()
    if not pi:
        raise HTTPException(status_code=404)
    if not _can_view(user, pi):
        raise HTTPException(status_code=403)
    if not pi.marca_imagem_path or not os.path.exists(pi.marca_imagem_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(
        pi.marca_imagem_path,
        media_type="application/octet-stream",
        filename=pi.marca_imagem_original_filename or os.path.basename(pi.marca_imagem_path),
    )


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


@router.get("/pis/{pi_id}/edit", name="pi_edit")
async def pi_edit_form(
    pi_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    pi = (
        db.query(PI)
        .options(
            selectinload(PI.authors).selectinload(PIAuthor.profile),
            selectinload(PI.owner),
        )
        .filter(PI.id == pi_id)
        .first()
    )
    if not pi:
        raise HTTPException(status_code=404)
    if pi.owner_id != user.id:
        raise HTTPException(status_code=403)
    if pi.status != PIStatus.awaiting_corrections:
        raise HTTPException(
            status_code=400,
            detail="Esta PI não está em correção no momento. Status atual: "
                   + (pi.status.value if pi.status else "desconhecido"),
        )

    primary_author = next((a for a in pi.authors if a.is_primary), None)
    profile = primary_author.profile if primary_author else None

    form_data = {
        "title": pi.title,
        "type": pi.type.value,
        "description": pi.description or "",
        "programming_language": pi.programming_language or "",
        "creation_date": pi.creation_date.isoformat() if pi.creation_date else "",
        "publication_date": pi.publication_date.isoformat() if pi.publication_date else "",
        "application_field": pi.application_field or "",
        "program_type": pi.program_type or "",
        "source_hash": pi.source_hash or "",
        "is_derived": pi.is_derived,
        "derived_title": pi.derived_title or "",
        "derived_registration": pi.derived_registration or "",
        "marca_nome": pi.marca_nome or "",
        "marca_tipo": pi.marca_tipo or "",
        "marca_idioma_estrangeiro": pi.marca_idioma_estrangeiro or False,
        "marca_termo_estrangeiro": pi.marca_termo_estrangeiro or "",
        "marca_traducao": pi.marca_traducao or "",
        "marca_termos_colidencia": pi.marca_termos_colidencia or "",
        "marca_nice": pi.marca_nice or "",
        "marca_viena": pi.marca_viena or "",
        "marca_protecao_indicada": pi.marca_protecao_indicada or False,
        "marca_protecao_justificativa": pi.marca_protecao_justificativa or "",
        "has_partner": pi.has_partner,
        "partner_name": pi.partner_name or "",
        "partner_cnpj": pi.partner_cnpj or "",
        "partner_contact": pi.partner_contact or "",
        "primary_percentage": str(float(primary_author.percentage)) if primary_author else "",
    }

    primary_data = _empty_primary()
    if profile:
        primary_data = {
            "cpf": profile.cpf,
            "rg": profile.rg,
            "birth_date": profile.birth_date.isoformat() if profile.birth_date else "",
            "nationality": profile.nationality,
            "marital_status": profile.marital_status,
            "occupation": profile.occupation,
            "phone": profile.phone or "",
            "cellphone": profile.cellphone,
            "address_street": profile.address_street,
            "address_number": profile.address_number,
            "address_district": profile.address_district,
            "address_city": profile.address_city,
            "address_state": profile.address_state,
            "address_zip": profile.address_zip,
            "ifms_bond": profile.ifms_bond.value if profile.ifms_bond else "",
            "ifms_bond_other": profile.ifms_bond_other or "",
            "campus": profile.campus or "",
        }

    coauthors = [
        {
            "name": a.name,
            "email": a.email,
            "percentage": str(float(a.percentage)),
            "institution": a.institution or "ifms",
        }
        for a in pi.authors if not a.is_primary
    ]

    return templates.TemplateResponse(
        request, "pi/new.html",
        {
            "user": user,
            "pi_types": PI_TYPE_LABELS,
            "ifms_bonds": IFMS_BOND_LABELS,
            "ifms_campuses": IFMS_CAMPUSES,
            "errors": [],
            "form": form_data,
            "primary": primary_data,
            "coauthors": coauthors,
            "accepted_truth": True,
            "accepted_confidentiality": True,
            "edit_mode": True,
            "pi_id": pi.id,
            "admin_notes": pi.admin_notes or "",
        },
    )


@router.post("/pis/{pi_id}/edit", name="pi_edit_submit")
async def pi_edit_submit(
    pi_id: int,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    pi = (
        db.query(PI)
        .options(
            selectinload(PI.authors).selectinload(PIAuthor.profile),
            selectinload(PI.documents),
        )
        .filter(PI.id == pi_id)
        .first()
    )
    if not pi:
        raise HTTPException(status_code=404)
    if pi.owner_id != user.id:
        raise HTTPException(status_code=403)
    # Duplo clique em "Salvar", abas em paralelo ou Voltar do navegador podem reenviar o
    # POST depois que a correção já foi aplicada (status já awaiting_signatures).
    if pi.status != PIStatus.awaiting_corrections:
        return RedirectResponse(
            url=f"/pis/{pi_id}?correcao_ja_enviada=1",
            status_code=303,
        )

    form = await request.form()

    title = (form.get("title") or "").strip()
    pi_type = (form.get("type") or "").strip()
    description = (form.get("description") or "").strip()

    programming_language = (form.get("programming_language") or "").strip()
    creation_date_raw = (form.get("creation_date") or "").strip()
    publication_date_raw = (form.get("publication_date") or "").strip()
    application_field = (form.get("application_field") or "").strip()
    program_type = (form.get("program_type") or "").strip()
    source_hash = (form.get("source_hash") or "").strip()
    is_derived = form.get("is_derived") in ("on", "true", "1")
    derived_title = (form.get("derived_title") or "").strip()
    derived_registration = (form.get("derived_registration") or "").strip()

    marca_nome = (form.get("marca_nome") or "").strip()
    marca_tipo = (form.get("marca_tipo") or "").strip()
    marca_idioma_estrangeiro = form.get("marca_idioma_estrangeiro") in ("on", "true", "1")
    marca_termo_estrangeiro = (form.get("marca_termo_estrangeiro") or "").strip()
    marca_traducao = (form.get("marca_traducao") or "").strip()
    marca_termos_colidencia = (form.get("marca_termos_colidencia") or "").strip()
    marca_nice = (form.get("marca_nice") or "").strip()
    marca_viena = (form.get("marca_viena") or "").strip()
    marca_protecao_indicada = form.get("marca_protecao_indicada") in ("on", "true", "1")
    marca_protecao_justificativa = (form.get("marca_protecao_justificativa") or "").strip()

    video_upload = form.get("video_file")
    source_code_upload = form.get("source_code_file")
    marca_imagem_upload = form.get("marca_imagem_file")

    has_partner = form.get("has_partner") in ("on", "true", "1")
    partner_name = (form.get("partner_name") or "").strip() or None
    partner_cnpj = (form.get("partner_cnpj") or "").strip() or None
    partner_contact = (form.get("partner_contact") or "").strip() or None
    primary_percentage = (form.get("primary_percentage") or "").strip()

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
        "campus": (form.get("campus") or "").strip(),
    }

    errors: List[str] = []

    if not title:
        errors.append("Informe o título da Propriedade Intelectual.")
    try:
        pi_type_enum = PIType(pi_type)
    except ValueError:
        pi_type_enum = PIType.outro
        errors.append("Tipo de Propriedade Intelectual inválido.")

    creation_date_val = None
    publication_date_val = None

    if pi_type_enum == PIType.software:
        if not programming_language:
            errors.append("Informe a linguagem de programação.")
        if not application_field:
            errors.append("Informe o campo de aplicação.")
        if not program_type:
            errors.append("Informe o tipo de programa.")
        if not source_hash:
            errors.append("Informe o hash do código-fonte.")
        if creation_date_raw:
            try:
                creation_date_val = datetime.strptime(creation_date_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Data de criação inválida.")
        if publication_date_raw:
            try:
                publication_date_val = datetime.strptime(publication_date_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Data de publicação inválida.")
        if not creation_date_raw and not publication_date_raw:
            errors.append("Informe a data de criação ou a data de publicação.")

    if pi_type_enum == PIType.marca:
        if not marca_nome:
            errors.append("Informe o nome da marca.")
        if not marca_tipo:
            errors.append("Selecione o tipo de marca.")

    try:
        primary_pct = float(primary_percentage.replace(",", "."))
    except ValueError:
        primary_pct = 0.0
        errors.append("Sua porcentagem (autor principal) é inválida.")

    primary_bond = None
    if primary["ifms_bond"]:
        try:
            primary_bond = IfmsBond(primary["ifms_bond"])
        except ValueError:
            errors.append("Vínculo IFMS do autor principal inválido.")

    primary_bd = None
    if primary["birth_date"]:
        try:
            primary_bd = datetime.strptime(primary["birth_date"], "%Y-%m-%d").date()
        except ValueError:
            errors.append("Data de nascimento do autor principal inválida.")

    if errors:
        logger.warning("Validação falhou ao editar PI %s: %s", pi_id, errors)
        coauthor_names = form.getlist("coauthor_name")
        coauthor_emails = form.getlist("coauthor_email")
        coauthor_percentages = form.getlist("coauthor_percentage")
        coauthor_institutions = form.getlist("coauthor_institution")
        return templates.TemplateResponse(
            request, "pi/new.html",
            {
                "user": user,
                "pi_types": PI_TYPE_LABELS,
                "ifms_bonds": IFMS_BOND_LABELS,
                "ifms_campuses": IFMS_CAMPUSES,
                "errors": errors,
                "form": {
                    "title": title, "type": pi_type, "description": description,
                    "programming_language": programming_language,
                    "creation_date": creation_date_raw, "publication_date": publication_date_raw,
                    "application_field": application_field, "program_type": program_type,
                    "source_hash": source_hash, "is_derived": is_derived,
                    "derived_title": derived_title, "derived_registration": derived_registration,
                    "marca_nome": marca_nome, "marca_tipo": marca_tipo,
                    "marca_idioma_estrangeiro": marca_idioma_estrangeiro,
                    "marca_termo_estrangeiro": marca_termo_estrangeiro,
                    "marca_traducao": marca_traducao, "marca_termos_colidencia": marca_termos_colidencia,
                    "marca_nice": marca_nice, "marca_viena": marca_viena,
                    "marca_protecao_indicada": marca_protecao_indicada,
                    "marca_protecao_justificativa": marca_protecao_justificativa,
                    "has_partner": has_partner, "partner_name": partner_name or "",
                    "partner_cnpj": partner_cnpj or "", "partner_contact": partner_contact or "",
                    "primary_percentage": primary_percentage,
                },
                "primary": primary,
                "accepted_truth": True,
                "accepted_confidentiality": True,
                "coauthors": [
                    {"name": n, "email": e, "percentage": p, "institution": coauthor_institutions[i] if i < len(coauthor_institutions) else "ifms"}
                    for i, (n, e, p) in enumerate(zip(coauthor_names, coauthor_emails, coauthor_percentages))
                    if (n or e or p)
                ],
                "edit_mode": True,
                "pi_id": pi_id,
                "admin_notes": pi.admin_notes or "",
            },
            status_code=400,
        )

    # Update PI fields
    pi.title = title
    pi.type = pi_type_enum
    pi.description = description or None
    pi.has_partner = has_partner
    pi.partner_name = partner_name if has_partner else None
    pi.partner_cnpj = partner_cnpj if has_partner else None
    pi.partner_contact = partner_contact if has_partner else None

    if pi_type_enum == PIType.software:
        pi.programming_language = programming_language or None
        pi.creation_date = creation_date_val
        pi.publication_date = publication_date_val
        pi.application_field = application_field or None
        pi.program_type = program_type or None
        pi.source_hash = source_hash or None
        pi.is_derived = is_derived
        pi.derived_title = derived_title or None if is_derived else None
        pi.derived_registration = derived_registration or None if is_derived else None

    if pi_type_enum == PIType.marca:
        pi.marca_nome = marca_nome or None
        pi.marca_tipo = marca_tipo or None
        pi.marca_idioma_estrangeiro = marca_idioma_estrangeiro
        pi.marca_termo_estrangeiro = marca_termo_estrangeiro or None
        pi.marca_traducao = marca_traducao or None
        pi.marca_termos_colidencia = marca_termos_colidencia or None
        pi.marca_nice = marca_nice or None
        pi.marca_viena = marca_viena or None
        pi.marca_protecao_indicada = marca_protecao_indicada
        pi.marca_protecao_justificativa = marca_protecao_justificativa or None

    # Handle file uploads (optional re-uploads during edit)
    pi_files_dir = os.path.join(settings.pi_files_storage_dir, f"pi_{pi.id}")
    if pi_type_enum == PIType.software:
        video_result = await save_flexible_upload(
            video_upload, os.path.join(pi_files_dir, "video", "video"),
            max_bytes=200 * 1024 * 1024,
            allowed_exts={"mp4", "avi", "mkv", "pdf", "docx", "zip", "rar"},
        )
        if video_result:
            pi.video_path, pi.video_original_filename, _ = video_result

        sc_result = await save_flexible_upload(
            source_code_upload, os.path.join(pi_files_dir, "source_code", "source"),
            max_bytes=200 * 1024 * 1024,
            allowed_exts={"zip", "rar", "7z", "tar", "gz"},
        )
        if sc_result:
            pi.source_code_path, pi.source_code_original_filename, _ = sc_result

    if pi_type_enum == PIType.marca:
        img_result = await save_flexible_upload(
            marca_imagem_upload, os.path.join(pi_files_dir, "marca", "imagem"),
            max_bytes=10 * 1024 * 1024,
            allowed_exts={"jpg", "jpeg", "png", "gif", "svg", "webp"},
        )
        if img_result:
            pi.marca_imagem_path, pi.marca_imagem_original_filename, _ = img_result

    # Update primary author profile
    primary_author = next((a for a in pi.authors if a.is_primary), None)
    if primary_author:
        primary_author.percentage = primary_pct
        if primary_author.profile:
            profile = primary_author.profile
            profile.cpf = primary["cpf"]
            profile.rg = primary["rg"]
            profile.birth_date = primary_bd
            profile.nationality = primary["nationality"]
            profile.marital_status = primary["marital_status"]
            profile.occupation = primary["occupation"]
            profile.phone = primary["phone"] or None
            profile.cellphone = primary["cellphone"]
            profile.address_street = primary["address_street"]
            profile.address_number = primary["address_number"]
            profile.address_district = primary["address_district"]
            profile.address_city = primary["address_city"]
            profile.address_state = primary["address_state"]
            profile.address_zip = primary["address_zip"]
            profile.ifms_bond = primary_bond
            profile.ifms_bond_other = primary["ifms_bond_other"] if primary_bond == IfmsBond.outros else None
            profile.campus = primary["campus"] if primary_bond != IfmsBond.outros else None

    # Clear admin notes and transition to awaiting_signatures
    pi.admin_notes = None
    pi.status = PIStatus.awaiting_signatures

    # Regenerate PDFs
    from app.services.pdf_service import generate_all_pdfs, all_authors_completed
    if all_authors_completed(pi):
        try:
            generate_all_pdfs(db, pi)
        except Exception:
            logger.exception("Falha ao regenerar PDFs para PI %s", pi_id)
        db.refresh(pi)

    # Notification for admin
    db.add(AdminNotification(
        pi_id=pi.id,
        type=NotificationType.correction_submitted,
        message=f"PI corrigida e resubmetida: {pi.title}",
    ))

    # Capture data for background task before commit closes session
    _pi_id = pi.id
    _pi_title = pi.title
    _pi_type_val = pi.type.value
    _owner_name = user.name
    _owner_email = user.email

    db.commit()

    async def _notify_admins():
        from app.services.email import EmailMessage, get_email_service
        for admin_email in settings.admin_emails_list:
            try:
                html = templates.get_template("emails/admin_new_pi.html").render(
                    pi_title=_pi_title, pi_type=_pi_type_val, pi_id=_pi_id,
                    owner_name=_owner_name, owner_email=_owner_email,
                    app_name=settings.app_name, base_url=settings.app_base_url,
                )
                await get_email_service().send(EmailMessage(
                    to=admin_email,
                    subject=f"[{settings.app_name}] PI corrigida: {_pi_title}",
                    html=html,
                ))
            except Exception as exc:  # noqa: BLE001
                logger.exception("Falha ao notificar admin: %s", exc)

    background.add_task(_notify_admins)

    return RedirectResponse(url=f"/pis/{pi_id}", status_code=303)
