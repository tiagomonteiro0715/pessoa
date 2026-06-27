"""OpenAPI 3.0 HTTP wrapper around the Pessoa chat.

Run with:  uv run python src/API/server.py
Then open http://127.0.0.1:8000/docs for the Swagger UI (spec at /openapi.json).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from chat import (  # noqa: E402
    USER_ID, build_memory, ensure_model_pulled, ensure_server_env, stream_answer,
)

ensure_server_env()
ensure_model_pulled()
_mem = build_memory()

app = FastAPI(
    title="Pessoa API",
    version="0.1.0",
    description="Local pt-PT chat with long-term memory (Ollama + mem0).",
)


class ChatRequest(BaseModel):
    prompt: str
    use_web: bool = False


@app.post("/chat", summary="Stream the assistant's answer, enriched with memory.")
def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_answer(_mem, req.prompt, use_web=req.use_web),
        media_type="text/plain; charset=utf-8",
    )


@app.get("/memory/search", summary="Top-k memory snippets relevant to `q`.")
def memory_search(q: str, top_k: int = 3):
    return _mem.search(q, filters={"user_id": USER_ID}, top_k=top_k).get("results", [])


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
