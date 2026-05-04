from __future__ import annotations

import logging
import os
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from sqlalchemy.orm import Session
from weasyprint import HTML

from app.config import settings
from app.models import Document, DocumentType, PI, PIAuthorStatus, PIType
from app.templating import templates

logger = logging.getLogger(__name__)


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


# Barra final obrigatória: urljoin com "static" sem / faz "img/x.png" resolver para
# static/irmão de img, não static/img/ — imagens falham e o PDF mostra o alt.
_static_path = (Path(__file__).resolve().parent.parent / "static").resolve()
_STATIC_BASE_URL = _static_path.as_uri() + "/"


def _render_pdf(template_name: str, context: dict, output_path: str) -> None:
    html = templates.get_template(template_name).render(**context)
    HTML(string=html, base_url=_STATIC_BASE_URL).write_pdf(output_path)


def all_authors_completed(pi: PI) -> bool:
    if not pi.authors:
        return False
    return all(pa.status == PIAuthorStatus.completed for pa in pi.authors)


def _pi_dir(pi: PI) -> str:
    p = os.path.join(settings.pdf_storage_dir, f"pi_{pi.id}")
    _ensure_dir(p)
    return p


def _replace_documents(db: Session, pi: PI, doc_type: DocumentType, items: list[Document]) -> None:
    """Remove documentos antigos do mesmo tipo e adiciona os novos."""
    for old in list(pi.documents):
        if old.type == doc_type:
            try:
                if os.path.exists(old.pdf_path):
                    os.remove(old.pdf_path)
            except OSError:
                logger.warning("Falha ao remover PDF antigo: %s", old.pdf_path)
            db.delete(old)
    db.flush()
    for d in items:
        db.add(d)
    db.flush()


def generate_all_pdfs(db: Session, pi: PI) -> list[Document]:
    """Gera (ou regenera) todos os PDFs (Anexos I, II, III, IV, V).

    - Anexo I: dados do programa (1 documento)
    - Anexo II: dados consolidados de todos os autores (1 documento)
    - Anexo III: declaração de veracidade (1 – autor principal)
    - Anexo IV: cessão de direitos (1 documento, com %)
    - Anexo V: termo de confidencialidade (1 por autor)
    """
    if not all_authors_completed(pi):
        raise ValueError("Nem todos os coautores concluíram o cadastro.")

    pi_dir = _pi_dir(pi)
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    docs: list[Document] = []

    # Anexo I
    out = os.path.join(pi_dir, f"anexo_i_{now_str}.pdf")
    _render_pdf("pdfs/anexo_i.html", {"pi": pi, "now": datetime.now(timezone.utc)}, out)
    doc = Document(pi_id=pi.id, type=DocumentType.anexo_i, pdf_path=out)
    docs.append(doc)
    _replace_documents(db, pi, DocumentType.anexo_i, [doc])

    # Anexo II
    out = os.path.join(pi_dir, f"anexo_ii_{now_str}.pdf")
    _render_pdf("pdfs/anexo_ii.html", {"pi": pi, "now": datetime.now(timezone.utc)}, out)
    doc = Document(pi_id=pi.id, type=DocumentType.anexo_ii, pdf_path=out)
    docs.append(doc)
    _replace_documents(db, pi, DocumentType.anexo_ii, [doc])

    out = os.path.join(pi_dir, f"anexo_iv_{now_str}.pdf")
    _render_pdf("pdfs/anexo_iv.html", {"pi": pi, "now": datetime.now(timezone.utc)}, out)
    doc = Document(pi_id=pi.id, type=DocumentType.anexo_iv, pdf_path=out)
    docs.append(doc)
    _replace_documents(db, pi, DocumentType.anexo_iv, [doc])

    primary_author = next((pa for pa in pi.authors if pa.is_primary), pi.authors[0])
    out = os.path.join(pi_dir, f"anexo_iii_autor_{primary_author.id}_{now_str}.pdf")
    _render_pdf(
        "pdfs/anexo_iii.html",
        {"pi": pi, "pa": primary_author, "now": datetime.now(timezone.utc)},
        out,
    )
    doc_iii = Document(
        pi_id=pi.id, type=DocumentType.anexo_iii,
        pdf_path=out, pi_author_id=primary_author.id,
    )
    _replace_documents(db, pi, DocumentType.anexo_iii, [doc_iii])
    docs.append(doc_iii)

    items = []
    for pa in pi.authors:
        out = os.path.join(pi_dir, f"anexo_v_autor_{pa.id}_{now_str}.pdf")
        _render_pdf(
            "pdfs/anexo_v.html",
            {"pi": pi, "pa": pa, "now": datetime.now(timezone.utc)},
            out,
        )
        items.append(
            Document(
                pi_id=pi.id, type=DocumentType.anexo_v,
                pdf_path=out, pi_author_id=pa.id,
            )
        )
    _replace_documents(db, pi, DocumentType.anexo_v, items)
    docs.extend(items)

    # Registro de Marca (only for marca-type PIs)
    if pi.type == PIType.marca:
        out = os.path.join(pi_dir, f"registro_marca_{now_str}.pdf")
        _render_pdf(
            "pdfs/registro_marca.html",
            {"pi": pi, "now": datetime.now(timezone.utc)},
            out,
        )
        doc_marca = Document(pi_id=pi.id, type=DocumentType.registro_marca, pdf_path=out)
        docs.append(doc_marca)
        _replace_documents(db, pi, DocumentType.registro_marca, [doc_marca])

    return docs


def build_zip_for_pi(pi: PI) -> BytesIO:
    """Empacota os PDFs do PI em um ZIP em memória (PDFs na raiz, sem subpastas)."""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc in pi.documents:
            if not os.path.exists(doc.pdf_path):
                continue
            zf.write(doc.pdf_path, arcname=os.path.basename(doc.pdf_path))
    buf.seek(0)
    return buf


def documents_by_type(pi: PI) -> dict[str, list[Document]]:
    out: dict[str, list[Document]] = {}
    for d in pi.documents:
        out.setdefault(d.type.value, []).append(d)
    return out
