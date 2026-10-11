from datetime import date
from pathlib import Path
import re
import sys


for parent in Path(__file__).resolve().parents:
    if (parent / "packages" / "shared" / "incident_validation.py").is_file():
        shared_root = str(parent)
        if shared_root not in sys.path:
            sys.path.insert(0, shared_root)
        break

from packages.shared.incident_validation import (
    INCIDENT_BRANCHES,
    INCIDENT_CATEGORIES,
    INCIDENT_ORIGINS,
    INCIDENT_STATUSES,
    IncidentValidationError,
    transform_csv_row,
    validate_incident_payload,
)


VALID_CATEGORIES = {
    "TECHNICAL",
    "BILLING",
    "ACCESS",
    "HR_QUERY",
    "COMPLAINT",
}

VALID_STATUSES = {
    "OPEN",
    "CLOSED",
    "DISCARDED",
}

AGENT_ID_PATTERN = re.compile(r"^AGT-\d{2}$")
TICKET_ID_PATTERN = re.compile(r"^NXV-(\d{6})$")


def generate_ticket_id(existing_ids: list[str]) -> str:
    highest_number = 0

    for ticket_id in existing_ids:
        match = TICKET_ID_PATTERN.fullmatch(ticket_id)
        if match:
            highest_number = max(
                highest_number,
                int(match.group(1)),
            )

    return f"NXV-{highest_number + 1:06d}"


def validate_incident_data(data: dict) -> dict:
    clean = {
        **data,
        "client_company": data["client_company"].strip(),
        "description": data["description"].strip(),
        "agent_id": data["agent_id"].strip(),
    }

    if not clean["client_company"]:
        raise ValueError("client_company es obligatorio")

    if clean["category"] not in VALID_CATEGORIES:
        raise ValueError("category no es válida")

    if len(clean["description"]) < 5:
        raise ValueError("description debe tener al menos 5 caracteres")

    if not AGENT_ID_PATTERN.fullmatch(clean["agent_id"]):
        raise ValueError("agent_id debe tener formato AGT-XX")

    if clean["status"] not in VALID_STATUSES:
        raise ValueError("status no es válido")

    if clean["status"] == "CLOSED" and clean["satisfaction_score"] is None:
        raise ValueError("CLOSED requiere satisfaction_score")

    score = clean["satisfaction_score"]
    if score is not None and not 1 <= score <= 5:
        raise ValueError("satisfaction_score debe estar entre 1 y 5")

    if not isinstance(clean["date"], date):
        raise ValueError("date debe ser una fecha válida")

    clean["date"] = clean["date"].isoformat()

    return clean
