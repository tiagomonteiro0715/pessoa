"""Test package for Pessoa.

The Ollama optimization env vars are pre-set here so that importing
`API.server` (which runs `ensure_server_env()` at module top) does NOT try to
bounce the Ollama daemon during a test run. Tests that need a real Ollama
will still fail at the first `ollama.list()` call if the daemon isn't up —
which is the correct behavior.
"""
import os

os.environ.setdefault("OLLAMA_FLASH_ATTENTION", "1")
os.environ.setdefault("OLLAMA_KV_CACHE_TYPE", "q4_0")
os.environ.setdefault("OLLAMA_KEEP_ALIVE", "45m")
