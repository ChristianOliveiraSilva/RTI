from __future__ import annotations

import os
from pathlib import Path

from fastapi import HTTPException
from starlette.datastructures import UploadFile


ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
}

ALLOWED_EXTS = {"pdf", "jpg", "jpeg", "png"}


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def _safe_ext(upload: UploadFile) -> str:
    name = (upload.filename or "").strip()
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext == "jpeg":
        ext = "jpg"
    if ext and ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail="Formato de arquivo inválido (use PDF/JPG/PNG).")
    if upload.content_type in ALLOWED_CONTENT_TYPES:
        return ALLOWED_CONTENT_TYPES[upload.content_type]
    if ext:
        return ext
    raise HTTPException(status_code=400, detail="Não foi possível identificar o tipo do arquivo.")


def _safe_ext_flexible(upload: UploadFile, allowed_exts: set[str]) -> str:
    """Extract and validate extension from upload against a custom allowed set."""
    name = (upload.filename or "").strip()
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext and ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Formato inválido. Permitidos: {', '.join(sorted(allowed_exts))}.",
        )
    if not ext:
        raise HTTPException(status_code=400, detail="Não foi possível identificar o tipo do arquivo.")
    return ext


async def save_required_upload(
    upload: UploadFile | None,
    dest_path_without_ext: str,
    *,
    max_bytes: int,
) -> tuple[str, str, str]:
    """Salva upload em disco e retorna (file_path, original_filename, content_type)."""
    if upload is None or not isinstance(upload, UploadFile) or not upload.filename:
        raise HTTPException(status_code=400, detail="Arquivo obrigatório não enviado.")

    ext = _safe_ext(upload)
    dest_path = f"{dest_path_without_ext}.{ext}"

    _ensure_dir(os.path.dirname(dest_path))

    wrote = 0
    try:
        with open(dest_path, "wb") as f:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                wrote += len(chunk)
                if wrote > max_bytes:
                    raise HTTPException(status_code=400, detail="Arquivo muito grande (limite: 10MB).")
                f.write(chunk)
    except Exception:
        try:
            if os.path.exists(dest_path):
                os.remove(dest_path)
        except OSError:
            pass
        raise

    return dest_path, upload.filename, upload.content_type or ""


async def save_flexible_upload(
    upload: UploadFile | None,
    dest_path_without_ext: str,
    *,
    max_bytes: int,
    allowed_exts: set[str],
) -> tuple[str, str, str] | None:
    """Save an optional file upload with custom extension validation.

    Returns None if no file was provided, or (file_path, original_filename, content_type).
    """
    if upload is None or not isinstance(upload, UploadFile) or not upload.filename:
        return None

    ext = _safe_ext_flexible(upload, allowed_exts)
    dest_path = f"{dest_path_without_ext}.{ext}"

    _ensure_dir(os.path.dirname(dest_path))

    wrote = 0
    try:
        with open(dest_path, "wb") as f:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                wrote += len(chunk)
                if wrote > max_bytes:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Arquivo muito grande (limite: {max_bytes // (1024*1024)}MB).",
                    )
                f.write(chunk)
    except Exception:
        try:
            if os.path.exists(dest_path):
                os.remove(dest_path)
        except OSError:
            pass
        raise

    return dest_path, upload.filename, upload.content_type or ""

