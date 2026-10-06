import unittest
from datetime import date
from unittest.mock import patch

from app.db import incidents
from app.incident_rules import generate_ticket_id, validate_incident_data
from app.main import forgot_password
from app.schemas import (
    ForgotPasswordRequest,
    IncidentCreate,
    IncidentPublic,
    IncidentStatusUpdate,
)
from app.security import create_reset_token, hash_reset_token


class IncidentRulesTests(unittest.TestCase):
    def valid_data(self):
        return {
            "date": date(2026, 9, 30),
            "client_company": "Cliente corporativo",
            "category": "TECHNICAL",
            "description": "Error de conexión en la aplicación",
            "agent_id": "AGT-07",
            "status": "OPEN",
            "satisfaction_score": None,
        }

    def test_validates_and_normalizes_ticket_data(self):
        data = self.valid_data()
        data["client_company"] = "  Cliente corporativo  "
        validated = validate_incident_data(data)
        self.assertEqual(validated["client_company"], "Cliente corporativo")
        self.assertEqual(validated["date"], "2026-09-30")

    def test_closed_ticket_requires_satisfaction_score(self):
        data = self.valid_data()
        data["status"] = "CLOSED"
        with self.assertRaises(ValueError):
            IncidentStatusUpdate.model_validate(data)

    def test_score_must_be_between_one_and_five(self):
        data = self.valid_data()
        data["satisfaction_score"] = 6
        with self.assertRaises(ValueError):
            IncidentStatusUpdate.model_validate(data)

    def test_date_requires_iso_format(self):
        data = self.valid_data()
        data.pop("date")
        data.update(
            {
                "date": "20260930",
                "customer_email": "",
            }
        )
        with self.assertRaises(ValueError):
            IncidentCreate.model_validate(data)

    def test_ticket_id_uses_next_sequence(self):
        self.assertEqual(
            generate_ticket_id(["NXV-000002", "invalid"]),
            "NXV-000003",
        )

    def test_nexova_incidents_use_an_isolated_table(self):
        self.assertEqual(incidents.name, "nexova_incidents")

    def test_public_ticket_schema_excludes_customer_email(self):
        public_data = {
            "id": 1,
            "ticket_id": "NXV-000001",
            "date": date(2026, 9, 30),
            "client_company": "Cliente corporativo",
            "category": "TECHNICAL",
            "description": "Error de conexión en la aplicación",
            "agent_id": "AGT-07",
            "status": "OPEN",
            "satisfaction_score": None,
            "reported_by_user_id": 1,
            "created_at": "2026-09-30T10:00:00+00:00",
            "updated_at": "2026-09-30T10:00:00+00:00",
        }
        ticket = IncidentPublic.model_validate(public_data)
        self.assertFalse(hasattr(ticket, "customer_email"))

    def test_reset_token_is_stored_as_a_one_way_hash(self):
        token = create_reset_token()
        token_hash = hash_reset_token(token)
        self.assertNotEqual(token, token_hash)
        self.assertEqual(len(token_hash), 64)

    def test_forgot_password_does_not_disclose_unknown_accounts(self):
        payload = ForgotPasswordRequest.model_construct(email="")
        with patch("app.main.users.search", return_value=[]):
            result = forgot_password(payload)
        self.assertEqual(
            result["message"],
            "Si la cuenta está registrada, recibirá un enlace para restablecer la contraseña.",
        )


if __name__ == "__main__":
    unittest.main()
