"""Contract tests for the FastAPI server.

What's verified: endpoint surface, status codes, the auto-generated OpenAPI
3.x spec, request-body validation. No LLM inference is triggered — these
should run in well under a second after the import warm-up.

Caveat: importing `API.server` runs `ensure_server_env()` and
`ensure_model_pulled()` at module top, so Ollama still needs to be installed
and reachable. The tests themselves just check schema and /health.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from API.server import app  # noqa: E402


class APIContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_returns_ok(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})

    def test_openapi_3_spec_is_served(self):
        r = self.client.get("/openapi.json")
        self.assertEqual(r.status_code, 200)
        spec = r.json()
        self.assertTrue(spec["openapi"].startswith("3."),
                        f"unexpected OpenAPI version: {spec['openapi']!r}")
        self.assertEqual(spec["info"]["title"], "Pessoa API")

    def test_required_endpoints_present_in_spec(self):
        spec = self.client.get("/openapi.json").json()
        for path in ("/chat", "/memory/search", "/health"):
            self.assertIn(path, spec["paths"], f"{path} missing from OpenAPI spec")

    def test_chat_body_requires_prompt(self):
        # FastAPI's pydantic validation: missing required field → 422.
        r = self.client.post("/chat", json={})
        self.assertEqual(r.status_code, 422)

    def test_chat_body_rejects_wrong_type(self):
        r = self.client.post("/chat", json={"prompt": 123})
        self.assertEqual(r.status_code, 422)

    def test_swagger_ui_is_served(self):
        r = self.client.get("/docs")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])


if __name__ == "__main__":
    unittest.main()
