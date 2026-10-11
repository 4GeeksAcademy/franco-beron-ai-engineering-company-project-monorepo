import importlib.util
import io
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.auth import get_current_user
from app.database import get_db
from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "seed_incidents.py"


def load_seed_incidents_module():
    spec = importlib.util.spec_from_file_location(
        "seed_incidents_module",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ErrorHandlingAuditTests(unittest.TestCase):
    def setUp(self):
        self.previous_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_current_user] = lambda: {"role": "admin"}
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def test_route_storage_failures_are_structured_and_sanitized(self):
        for path, target in [
            ("/suppliers", "app.routers.suppliers.suppliers.all"),
            ("/api/incidents", "app.routers.incidents.central_incidents.all"),
            ("/api/tickets", "app.main.incidents.all"),
        ]:
            with self.subTest(path=path), patch(target, side_effect=OSError("private@example.com /internal/path")):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 500)
                self.assertEqual(response.json()["detail"]["error"], "operation_failed")
                self.assertNotIn("private@", response.text)
                self.assertNotIn("/internal", response.text)

    def test_inventory_failure_rolls_back_and_returns_503(self):
        session = Mock()
        session.exec.side_effect = OperationalError("secret", {}, Exception("secret"))
        app.dependency_overrides[get_db] = lambda: session
        response = self.client.get("/inventory/products")
        self.assertEqual(response.status_code, 503)
        session.rollback.assert_called_once()
        self.assertNotIn("secret", response.text)

    def test_not_found_and_validation_status_are_preserved(self):
        with patch("app.routers.suppliers.suppliers.get", return_value=None):
            self.assertEqual(self.client.get("/suppliers/123").status_code, 404)
        response = self.client.post("/suppliers", json={"contact_email": "private@example.com"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("private@", response.text)

    def test_seed_incidents_reports_missing_input_to_stderr(self):
        module = load_seed_incidents_module()
        missing_csv = REPO_ROOT / "data" / "missing-incidents.csv"

        with patch("sys.stderr", new_callable=io.StringIO) as stderr:
            with self.assertRaises(SystemExit) as context:
                module.load_csv_rows(missing_csv)

        self.assertEqual(context.exception.code, 1)
        self.assertIn("Error:", stderr.getvalue())
        self.assertIn("missing-incidents.csv", stderr.getvalue())

    def test_invalid_csv_does_not_expose_contents(self):
        module = load_seed_incidents_module()
        with TemporaryDirectory() as directory:
            source = Path(directory) / "input.csv"
            for content in (b"private@example.com\n", b"\xff\xfe", b'date,description\n"unterminated'):
                source.write_bytes(content)
                with patch("sys.stderr", new_callable=io.StringIO) as stderr:
                    with self.assertRaises(SystemExit) as caught:
                        module.load_csv_rows(source)
                self.assertEqual(caught.exception.code, 1)
                self.assertNotIn("private@example.com", stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
