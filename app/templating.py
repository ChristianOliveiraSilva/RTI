from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mato Grosso do Sul: UTC-4 (sem horario de verao no Brasil vigente a partir de 2019)
_MS_TZ = timezone(timedelta(hours=-4), "GMT-4")

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
        # Exibição padrão do sistema: fuso de MS (UTC-4)
        # Se vier sem tzinfo, assume UTC (como no banco) antes de converter.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(_MS_TZ).strftime(fmt)
    return str(value)


def format_datetime_ms(value: Any, fmt: str = "%d/%m/%Y %H:%M") -> str:
    """Data/hora no fuso de MS (UTC-4), ex. e-mail e prazo de convite."""
    if value is None:
        return ""
    if not isinstance(value, datetime):
        return str(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_MS_TZ).strftime(fmt)


def format_date_ms(value: Any, fmt: str = "%d/%m/%Y") -> str:
    """Data no fuso de MS (UTC-4), sem horário."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(_MS_TZ).strftime(fmt)
    if isinstance(value, date):
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
templates.env.filters["fdatetime_ms"] = format_datetime_ms
templates.env.filters["fdate_ms"] = format_date_ms
templates.env.filters["fpercent"] = format_percent
templates.env.filters["status_label"] = status_label
templates.env.filters["pi_type_label"] = pi_type_label
templates.env.filters["ifms_bond_label"] = ifms_bond_label

templates.env.globals["PI_TYPE_LABELS"] = PI_TYPE_LABELS
templates.env.globals["IFMS_BOND_LABELS"] = IFMS_BOND_LABELS
templates.env.globals["STATUS_LABELS"] = STATUS_LABELS
