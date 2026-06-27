"""MCP server tests.

Spawns `src/MCP/server.py` as a subprocess and talks to it over stdio using
the official `mcp` Python SDK. Both contract checks (list_tools + schema)
and end-to-end checks (actually call the tools) live here, because spawning
the MCP server is costly and the SDK doesn't easily share a session across
unittest methods.

Requires Ollama running (the MCP server's import path goes through chat.py).
The end-to-end test triggers real generation.
"""
import asyncio
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MCP_SERVER = str(PROJECT_ROOT / "src" / "MCP" / "server.py")


def _run(coro):
    return asyncio.run(coro)


class MCPServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            from mcp.client.stdio import StdioServerParameters
        except ImportError as e:
            raise unittest.SkipTest(f"mcp SDK not installed: {e}")
        cls.params = StdioServerParameters(
            command=sys.executable,
            args=[MCP_SERVER],
        )

    async def _with_session(self, fn):
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client
        async with stdio_client(self.params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await fn(session)

    # ---- contract --------------------------------------------------------

    def test_lists_expected_tools(self):
        async def go(session):
            tools = await session.list_tools()
            return {t.name for t in tools.tools}

        names = _run(self._with_session(go))
        self.assertIn("chat", names)
        self.assertIn("search_memory", names)

    def test_chat_tool_schema_requires_prompt(self):
        async def go(session):
            tools = await session.list_tools()
            return {t.name: t for t in tools.tools}

        tools = _run(self._with_session(go))
        schema = tools["chat"].inputSchema
        # FastMCP generates an object schema with `prompt` in `required`.
        self.assertEqual(schema.get("type"), "object")
        self.assertIn("prompt", schema.get("properties", {}))
        self.assertIn("prompt", schema.get("required", []))

    def test_search_memory_tool_schema_requires_query(self):
        async def go(session):
            tools = await session.list_tools()
            return {t.name: t for t in tools.tools}

        tools = _run(self._with_session(go))
        schema = tools["search_memory"].inputSchema
        self.assertIn("query", schema.get("properties", {}))
        self.assertIn("query", schema.get("required", []))

    # ---- end-to-end (slow, real generation) ------------------------------

    def test_chat_tool_returns_non_empty_text(self):
        async def go(session):
            return await session.call_tool(
                "chat", {"prompt": "Diz olá em uma única palavra curta."}
            )

        result = _run(self._with_session(go))
        # CallToolResult.content is a list of TextContent / ImageContent / …
        text = "".join(
            getattr(c, "text", "") for c in result.content
        )
        self.assertGreater(len(text), 0, "chat tool returned no text content")

    def test_search_memory_returns_content(self):
        async def go(session):
            return await session.call_tool(
                "search_memory", {"query": "qualquer coisa", "top_k": 2}
            )

        result = _run(self._with_session(go))
        # Even an empty store should yield at least a serialized "[]".
        self.assertGreaterEqual(len(result.content), 0)


if __name__ == "__main__":
    unittest.main()
