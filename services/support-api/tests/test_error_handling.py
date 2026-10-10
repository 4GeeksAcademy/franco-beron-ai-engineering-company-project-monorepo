import importlib.util
import io
import unittest
from pathlib import Path
from unittest.mock import patch

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
    def test_seed_incidents_reports_missing_input_to_stderr(self):
        module = load_seed_incidents_module()
        missing_csv = REPO_ROOT / "data" / "missing-incidents.csv"

        with patch("sys.stderr", new_callable=io.StringIO) as stderr:
            with self.assertRaises(SystemExit) as context:
                module.load_csv_rows(missing_csv)

        self.assertEqual(context.exception.code, 1)
        self.assertIn("Error:", stderr.getvalue())
        self.assertIn("missing-incidents.csv", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
