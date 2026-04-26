from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


PI_TYPE_LABELS = {
    "software": "Programa de Computador (Software)",
    "patente": "Patente",
    "desenho_industrial": "Desenho Industrial",
    "marca": "Marca",
    "cultivar": "Cultivar",
    "topografia": "Topografia de Circuitos",
    "outro": "Outro",
}

IFMS_BOND_LABELS = {
    "servidor": "Servidor",
    "estudante": "Estudante",
    "outros": "Outros",
}

STATUS_LABELS = {
    "draft": "Rascunho",
    "awaiting_authors": "Aguardando coautores",
    "completed": "Concluído",
    "pending": "Pendente",
}


def format_date(value: Any, fmt: str = "%d/%m/%Y") -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, date):
        return value.strftime(fmt)
    return str(value)


def format_datetime(value: Any, fmt: str = "%d/%m/%Y %H:%M") -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime(fmt)
    return str(value)


def format_percent(value: Any) -> str:
    if value is None:
        return "0%"
    try:
        return f"{float(value):.2f}".rstrip("0").rstrip(".") + "%"
    except (TypeError, ValueError):
        return f"{value}%"


def status_label(value: Any) -> str:
    if value is None:
        return ""
    key = value.value if hasattr(value, "value") else str(value)
    return STATUS_LABELS.get(key, key)


def pi_type_label(value: Any) -> str:
    if value is None:
        return ""
    key = value.value if hasattr(value, "value") else str(value)
    return PI_TYPE_LABELS.get(key, key)


def ifms_bond_label(value: Any) -> str:
    if value is None:
        return ""
    key = value.value if hasattr(value, "value") else str(value)
    return IFMS_BOND_LABELS.get(key, key)


templates.env.filters["fdate"] = format_date
templates.env.filters["fdatetime"] = format_datetime
templates.env.filters["fpercent"] = format_percent
templates.env.filters["status_label"] = status_label
templates.env.filters["pi_type_label"] = pi_type_label
templates.env.filters["ifms_bond_label"] = ifms_bond_label

templates.env.globals["PI_TYPE_LABELS"] = PI_TYPE_LABELS
templates.env.globals["IFMS_BOND_LABELS"] = IFMS_BOND_LABELS
templates.env.globals["STATUS_LABELS"] = STATUS_LABELS
