"""End-to-end tests for the FastAPI server.

Each test triggers real Ollama generation. Slow — seconds per assertion.
Requires Ollama running with `gemma4:e2b` and `nomic-embed-text` pulled.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from API.server import app  # noqa: E402


class APIEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_chat_returns_streamed_text(self):
        r = self.client.post("/chat", json={
            "prompt": "Diz olá em uma única palavra curta.",
        })
        self.assertEqual(r.status_code, 200)
        # TestClient collects the streamed body into r.text/r.content.
        self.assertGreater(len(r.text), 0, "chat returned an empty body")

    def test_chat_with_web_flag_returns_text(self):
        r = self.client.post("/chat", json={
            "prompt": "Diz olá.",
            "use_web": False,
        })
        self.assertEqual(r.status_code, 200)
        self.assertGreater(len(r.text), 0)

    def test_memory_search_returns_list_shape(self):
        r = self.client.get("/memory/search",
                            params={"q": "qualquer coisa", "top_k": 2})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIsInstance(body, list,
                              f"expected list, got {type(body).__name__}")
        # Each result is a dict with at least an 'id' and 'memory' field —
        # but the store may be empty, so only assert shape if non-empty.
        if body:
            self.assertIn("memory", body[0])

    def test_memory_search_default_top_k(self):
        r = self.client.get("/memory/search", params={"q": "olá"})
        self.assertEqual(r.status_code, 200)
        self.assertLessEqual(len(r.json()), 3)  # default top_k=3 per server.py


if __name__ == "__main__":
    unittest.main()
