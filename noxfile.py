"""Nox sessions for the Pessoa test suite.

Each session is an isolated venv. Nox owns the *which test layer* axis;
tox owns the *which Python version* axis (it only runs the cheap contract
tests there — see tox.ini).

Usage:

    nox -l                  # list available sessions
    nox -s contract         # fast OpenAPI/contract checks (no LLM)
    nox -s api_e2e          # POST /chat, /memory/search; triggers Ollama
    nox -s api_limits       # concurrency sweep — REQUIRES API running externally
    nox -s mcp              # MCP server: contract + e2e

The api_limits session expects the API server to be already running at
http://127.0.0.1:8000. Start it with `uv run python src/API/server.py`.
"""
import nox

PY = "3.12"


@nox.session(python=PY)
def contract(session):
    """API contract checks. Fast. Does not call the LLM."""
    session.install(".")
    session.run("python", "-m", "unittest", "tests.test_api_contract", "-v")


@nox.session(python=PY)
def api_e2e(session):
    """API end-to-end. Triggers real Ollama inference; ~10–30s per assertion."""
    session.install(".")
    session.run("python", "-m", "unittest", "tests.test_api_e2e", "-v")


@nox.session(python=PY)
def api_limits(session):
    """Concurrency/limits sweep. Requires API running at 127.0.0.1:8000."""
    session.install(".", "httpx")
    session.run("python", "-m", "unittest", "tests.test_api_limits", "-v")


@nox.session(python=PY)
def mcp(session):
    """MCP server: tools list + actual tool invocations. Slow."""
    session.install(".")
    session.run("python", "-m", "unittest", "tests.test_mcp", "-v")
