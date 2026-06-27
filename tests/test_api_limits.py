"""Limit/concurrency characterization for the FastAPI server.

Unlike the other test modules, this one talks to a REAL HTTP server (not
FastAPI's in-process TestClient) so we can measure honest wall-clock
behavior under concurrent load. Start the server first:

    uv run python src/API/server.py

…then in a separate terminal:

    nox -s api_limits          # or: python -m unittest tests.test_api_limits -v

If the server isn't reachable, the whole TestCase is skipped (so this won't
break a casual `python -m unittest discover tests`).

What we measure: latency for one request, then latency progression at
concurrency = 1, 2, 4. Ollama serves one request at a time per model, so
expect roughly linear queueing — the value of this test is putting numbers
on it so regressions show up.
"""
import asyncio
import time
import unittest

import httpx

API_BASE = "http://127.0.0.1:8000"
PROMPT = "Diz olá em uma única palavra curta."


def _server_up() -> bool:
    try:
        return httpx.get(f"{API_BASE}/health", timeout=1.0).status_code == 200
    except Exception:
        return False


@unittest.skipUnless(
    _server_up(),
    f"API server not running at {API_BASE}. "
    f"Start with: `uv run python src/API/server.py`",
)
class APILimits(unittest.TestCase):

    def test_single_request_baseline(self):
        async def go():
            async with httpx.AsyncClient(timeout=60.0) as c:
                t0 = time.perf_counter()
                r = await c.post(f"{API_BASE}/chat", json={"prompt": PROMPT})
                return time.perf_counter() - t0, r.status_code, len(r.text)

        elapsed, status, n = asyncio.run(go())
        self.assertEqual(status, 200)
        self.assertGreater(n, 0)
        print(f"\n[limits] baseline:  1 req → {elapsed:5.2f}s, {n} chars")

    def test_concurrent_sweep(self):
        """Fire N requests in parallel for N in {1, 2, 4} and print the
        wall-clock and per-request average. With Ollama's one-at-a-time
        scheduling, wall-clock should grow ~linearly with N."""

        async def fire(client, idx):
            t0 = time.perf_counter()
            r = await client.post(f"{API_BASE}/chat",
                                  json={"prompt": f"{PROMPT} ({idx})"})
            return time.perf_counter() - t0, r.status_code

        async def go(n):
            async with httpx.AsyncClient(timeout=180.0) as c:
                tasks = [fire(c, i) for i in range(n)]
                return await asyncio.gather(*tasks)

        for n in (1, 2, 4):
            wall_start = time.perf_counter()
            results = asyncio.run(go(n))
            wall = time.perf_counter() - wall_start
            statuses = {s for _, s in results}
            avg = sum(t for t, _ in results) / n
            print(f"[limits] N={n:<2d}        → "
                  f"wall {wall:5.2f}s, avg/req {avg:5.2f}s, "
                  f"statuses={statuses}")
            self.assertEqual(statuses, {200},
                             f"some requests failed at N={n}: {statuses}")

    def test_health_under_chat_load(self):
        """/health should stay fast even while /chat is busy — it does no
        LLM work. This guards against accidental global locks in server.py."""

        async def chat(client):
            await client.post(f"{API_BASE}/chat", json={"prompt": PROMPT},
                              timeout=180.0)

        async def health_ping(client):
            t0 = time.perf_counter()
            r = await client.get(f"{API_BASE}/health", timeout=5.0)
            return time.perf_counter() - t0, r.status_code

        async def go():
            async with httpx.AsyncClient() as c:
                chat_task = asyncio.create_task(chat(c))
                await asyncio.sleep(0.2)  # let /chat get going
                elapsed, status = await health_ping(c)
                await chat_task
                return elapsed, status

        elapsed, status = asyncio.run(go())
        self.assertEqual(status, 200)
        self.assertLess(elapsed, 1.0,
                        f"/health blocked for {elapsed:.2f}s while /chat ran")
        print(f"[limits] /health while busy → {elapsed*1000:.0f}ms")


if __name__ == "__main__":
    unittest.main()
