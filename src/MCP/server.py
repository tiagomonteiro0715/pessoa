"""MCP server exposing the Pessoa chat over stdio.

Run with:  uv run python src/MCP/server.py
Configure your MCP client (e.g. Claude Desktop) to spawn this script.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from chat import (  # noqa: E402
    USER_ID, build_memory, ensure_model_pulled, ensure_server_env, stream_answer,
)

ensure_server_env()
ensure_model_pulled()
_mem = build_memory()

server = FastMCP("pessoa")


@server.tool()
def chat(prompt: str, use_web: bool = False) -> str:
    """Send a prompt to Pessoa and return the full answer."""
    return "".join(stream_answer(_mem, prompt, use_web=use_web))


@server.tool()
def search_memory(query: str, top_k: int = 3) -> list:
    """Return top-k memory snippets relevant to `query`."""
    return _mem.search(query, filters={"user_id": USER_ID}, top_k=top_k).get("results", [])


if __name__ == "__main__":
    server.run()
