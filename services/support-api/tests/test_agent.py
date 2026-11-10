import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.main import app


class AgentEndpointTests(unittest.TestCase):
    def setUp(self):
        self.previous_overrides = app.dependency_overrides.copy()
        self.user = SimpleNamespace(doc_id=731)
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def test_query_requires_authentication(self):
        app.dependency_overrides.pop(get_current_user, None)

        response = self.client.post(
            "/agent/query",
            json={"question": "¿Cuál es el SLA comprometido con clientes?"},
        )

        self.assertEqual(response.status_code, 401)

    def test_query_returns_checkpointed_trace_and_trace_is_readable(self):
        response = self.client.post(
            "/agent/query",
            json={"question": "¿Cuál es el SLA comprometido con clientes?"},
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["checkpoint"]["available"])
        self.assertIn("24 horas", result["answer"])
        self.assertEqual(
            [event["node"] for event in result["trace"]],
            ["receive_question", "retrieve", "generate_answer"],
        )

        trace_response = self.client.get(
            f"/agent/traces/{result['thread_id']}"
        )
        self.assertEqual(trace_response.status_code, 200)
        self.assertEqual(trace_response.json()["trace"], result["trace"])

    def test_trace_is_scoped_to_the_authenticated_user(self):
        response = self.client.post(
            "/agent/query",
            json={"question": "¿Cuál es el SLA comprometido con clientes?"},
        )
        self.user.doc_id = 732

        trace_response = self.client.get(
            f"/agent/traces/{response.json()['thread_id']}"
        )
        self.assertEqual(trace_response.status_code, 404)

    def test_graph_errors_are_sanitized_by_the_endpoint(self):
        with patch(
            "app.routers.agent.run_agent",
            side_effect=RuntimeError("private implementation detail"),
        ):
            response = self.client.post(
                "/agent/query",
                json={"question": "consulta"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private implementation detail", response.text)
        self.assertNotIn("Traceback", response.text)


if __name__ == "__main__":
    unittest.main()