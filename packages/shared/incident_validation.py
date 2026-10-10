from datetime import datetime, timezone
import re


INCIDENT_CATEGORIES = {
    "technical_failure",
    "process_error",
    "client_complaint",
    "candidate_issue",
    "staff_issue",
    "sla_breach",
    "data_quality",
    "other",
}
INCIDENT_STATUSES = {"open", "in_progress", "resolved", "discarded"}
INCIDENT_ORIGINS = {"customer", "branch", "internal"}
INCIDENT_BRANCHES = {
    "central",
    "valencia_operations",
    "miami_office",
    "remote",
}

CSV_STATUS_MAP = {
    "OPEN": "open",
    "CLOSED": "resolved",
    "DISCARDED": "discarded",
}
CSV_CATEGORY_MAP = {
    "TECHNICAL": "technical_failure",
    "BILLING": "process_error",
    "ACCESS": "technical_failure",
    "HR_QUERY": "process_error",
    "COMPLAINT": "client_complaint",
}
CSV_AGENT_ID_PREFIX = "AGT-"


class IncidentValidationError(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


def validate_incident_payload(data: dict) -> dict:
    required_fields = (
        "title",
        "description",
        "category",
        "status",
        "origin",
        "branch",
    )
    for field in required_fields:
        if field not in data:
            raise IncidentValidationError(field, f"{field} es obligatorio.")

    clean = {**data}
    for field in ("title", "description"):
        value = clean[field]
        if not isinstance(value, str) or not value.strip():
            raise IncidentValidationError(field, f"{field} es obligatorio.")
        clean[field] = value.strip()

    if len(clean["title"]) > 120:
        raise IncidentValidationError("title", "El título admite hasta 120 caracteres.")
    if clean["category"] not in INCIDENT_CATEGORIES:
        raise IncidentValidationError("category", "La categoría no es válida.")
    if clean["status"] not in INCIDENT_STATUSES:
        raise IncidentValidationError("status", "El estado no es válido.")
    if clean["origin"] not in INCIDENT_ORIGINS:
        raise IncidentValidationError("origin", "El origen no es válido.")
    if clean["branch"] not in INCIDENT_BRANCHES:
        raise IncidentValidationError("branch", "La sede no es válida.")
    return clean


def transform_csv_row(row: dict) -> tuple[str, dict]:
    issues = []

    client_company = (row.get("client_company") or "").strip()
    if not client_company:
        issues.append("client_company")

    category = CSV_CATEGORY_MAP.get((row.get("category") or "").strip())
    if category is None:
        issues.append("category")

    description = row.get("description") or ""
    if len(description.strip()) < 5:
        issues.append("description")
    title = description[:120].strip()
    if not title:
        issues.append("title")

    agent_id = (row.get("agent_id") or "").strip()
    if (
        len(agent_id) != len(CSV_AGENT_ID_PREFIX) + 2
        or not agent_id.startswith(CSV_AGENT_ID_PREFIX)
        or not agent_id[-2:].isdigit()
    ):
        issues.append("agent_id")

    email = (row.get("customer_email") or "").strip()
    if "@" not in email:
        issues.append("customer_email")

    raw_status = (row.get("status") or "").strip()
    status = CSV_STATUS_MAP.get(raw_status)
    if status is None:
        issues.append("status")

    raw_score = (row.get("satisfaction_score") or "").strip()
    score = None
    if raw_score:
        try:
            score = int(raw_score)
            if score < 1 or score > 5:
                issues.append("satisfaction_score")
        except ValueError:
            issues.append("satisfaction_score")
    elif raw_status == "CLOSED":
        issues.append("satisfaction_score")

    raw_date = (row.get("date") or "").strip()
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
            raise ValueError
        created_at = datetime.strptime(raw_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        ).isoformat()
    except ValueError:
        created_at = ""
        issues.append("date")

    if issues:
        raise IncidentValidationError(", ".join(dict.fromkeys(issues)), "La fila CSV no cumple las reglas del analizador.")

    incident = validate_incident_payload(
        {
            "title": title,
            "description": description,
            "category": category,
            "status": status,
            "origin": "customer",
            "branch": "central",
        }
    )
    incident["description"] = description
    incident["created_at"] = created_at
    incident["updated_at"] = created_at

    ticket_id = (row.get("ticket_id") or "").strip()
    if ticket_id and not re.fullmatch(r"NXV-\d{6}", ticket_id):
        raise IncidentValidationError(
            "ticket_id",
            "El identificador del CSV no es válido.",
        )
    source_key = ticket_id or f"{incident['title']}|{created_at}"
    return source_key, incident