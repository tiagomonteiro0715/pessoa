# Pessoa: Local, LLM Agnostic AI Agent Infrastructure

The Manifesto: In the EU, infrastructure should be prioritized instead of base models

Historically, computing evolved from silicon chips to PCs, then to the internet. 

In mid-2026, we are witnessing the next shift!

AI is moving from raw models to agentic infrastructure, giving way to world models and physical AI.

It is crucial for Portugal and the EU to show initiative. However, they should be pragmatic. 

The common critique is that the US and China innovate while the EU regulates. 

Instead of waiting for a sovereign European foundation model, the EU can achieve data privacy and great performance by wrapping powerful global open-source models (like Gemma) in local infrastructure.

Pessoa is a blueprint for this pragmatic approach. 

It uses Gemma 4 (can be changed for any other LLM) while using system prompts (currently only Portuguese ones) to enforce local outputs (like pt-PT). 

This way, by the LLM knowing English as its foundational language, it can interact with the web and other services via APIs and MCPs, and its output defines the language spoken via system prompts.

### The Stack & Architecture
This project is an architectural template. For this reason, it has few API endpoints and only the basic Streamlit frontend needed for an LLM interface.

Also, with pyproject.toml and uv for seamless, version-locked, it is very easy to install all needed libraries, and the memory layer (mem0 + qdrant) is decoupled from the inference engine. So if you want to switch Ollama for vLLM for anything else, you can!

Finally, it runs 100% locally, and it uses FastAPI and FastMCP to allow integrations with services.

## Table of contents

- [Why is this called "Pessoa"?](#why-pessoa)
- How can I use this project
- [Requirements](#requirements)
- [Run](#run)
- [Project structure](#project-structure)
- [Configuration](#configuration)
- [How memory works](#how-memory-works)
- [Performance notes](#performance-notes)
- [License](#license)

## Why is this project called "Pessoa"?

![image of fernando pessoa](https://github.com/tiagomonteiro0715/pessoa/blob/main/fernando.jpg))

Named after **Fernando António Nogueira de Seabra Pessoa** (13 June 1888 to 30 November 1935), regarded as one of the most important Portuguese literary figures of the 20th century and one of the greatest poets in the Portuguese language. *Pessoa* also means "person" in Portuguese.

What makes the name especially great is Pessoa's invention of **heteronyms**. Heteronyms are not pseudonyms. You can think of them as alternate personas with their own biographies, styles, and opinions. He wrote under roughly seventy-five of them. Three that stand out:

 - **Alberto Caeiro**
 - **Álvaro de Campos**
 - **Ricardo Reis**

An LLM driven by a tuned system prompt is doing the same trick in miniature: stepping into a defined persona to write. 

This project leans into many personas! In this case the persona lives in [src/system_prompt.py](src/system_prompt.py) and is what makes the assistant sound like *Pessoa* rather than a default chatbot.

## How can I use this project? 

- **Streamlit chat UI** — multi-chat sidebar (search, inline rename, date
  groups, kebab actions, "Mostrar mais"), streaming answers, *Parar geração*,
  animated typing indicator, a streaming-dot on the active chat, image/audio
  attachments, optional live web/weather lookup.
- **OpenAPI HTTP API** ([src/API/server.py](src/API/server.py)) — a FastAPI
  wrapper exposing `/chat`, `/memory/search`, and `/health`; Swagger UI at
  `/docs`, OpenAPI 3.0 spec at `/openapi.json`.
- **MCP server** ([src/MCP/server.py](src/MCP/server.py)) — Model Context
  Protocol over stdio, with `chat` and `search_memory` tools that any MCP
  client (Claude Desktop, etc.) can call — including via Claude skills.

## Requirements

- [Ollama](https://ollama.com) installed (the launcher pulls models on first run).
- [uv](https://github.com/astral-sh/uv) for dependency management.

## Run

#### Install dependencies

```bash
uv sync
```

#### Launch the Streamlit UI (the usual way)

```bash
uv run python main.py
```

`main.py` ensures Ollama is up with the right env vars, pulls `gemma4:e2b` and
`nomic-embed-text` if missing, then runs `streamlit run src/app.py`. Open
http://localhost:8501.

Equivalent direct command (skips the bootstrap):

```bash
uv run streamlit run src/app.py
```

#### Run the HTTP API

```bash
uv run python src/API/server.py
```

Then open http://127.0.0.1:8000/docs.

#### Run the MCP server

```bash
uv run python src/MCP/server.py
```

For Claude Desktop, add it to your MCP config:

```json
{
  "mcpServers": {
    "pessoa": {
      "command": "uv",
      "args": ["run", "python", "/absolute/path/to/src/MCP/server.py"]
    }
  }
}
```

## Project structure

| File | Purpose |
|------|---------|
| `main.py` | Launcher: ensure Ollama is up, pull models, run the Streamlit UI. |
| `src/app.py` | Streamlit chat UI (layout, multi-chat state, streaming). |
| `src/chat.py` | Shared logic: model config, memory, Ollama setup, streaming. |
| `src/system_prompt.py` | Persona / language / safety prompt (pt-PT). |
| `src/styles.css` | Dark theme + sidebar styling for the Streamlit app. |
| `src/API/server.py` | FastAPI server (OpenAPI 3.0 spec at `/openapi.json`). |
| `src/MCP/server.py` | MCP server over stdio (`chat`, `search_memory` tools). |
| `pessoa_qdrant/` | Local [Qdrant](https://qdrant.tech) vector store on disk (persists memory across restarts). |

## Configuration

Tunables live at the top of [src/chat.py](src/chat.py):

| Setting | Default | Notes |
|---------|---------|-------|
| `MODEL` | `gemma4:e2b` | Chat model. |
| `EMBED_MODEL` | `nomic-embed-text` | Embeddings for memory search. |
| `NUM_CTX` | `8192` | Context window. Larger = more context but slower / heavier. |
| `KEEP_ALIVE` | `45m` | How long Ollama keeps the model warm in memory. |
| `USER_ID` | `pessoa` | mem0 user id; change to keep separate memory stores. |
| `STOP` | Llama stop tokens | No-op for Gemma; adjust if you switch model family. |

The system prompt lives in [src/system_prompt.py](src/system_prompt.py); the
Streamlit theme lives in [src/styles.css](src/styles.css).

Ollama optimization env vars (`OLLAMA_FLASH_ATTENTION=1`,
`OLLAMA_KV_CACHE_TYPE=q4_0`, `OLLAMA_KEEP_ALIVE=45m`) are applied automatically
by `ensure_server_env()`, which restarts the Ollama daemon so it picks them up.

## How memory works

1. On each prompt, the top-k relevant memories are retrieved (`mem.search`) and
   prepended to the model's context as *"Memória relevante"*.
2. After the answer streams, the exchange is stored **in the background** with
   `infer=False` — saved as a raw snippet without an LLM extraction pass, so
   memory writes never block (or compete with) your next prompt.

> Trade-off: because `infer=False` stores raw snippets, the vector space can
> accumulate redundant chat noise over time. Planned improvement: an async
> background worker (`asyncio`) that, when the system is idle, periodically
> aggregates and condenses those memories with the LLM.

Under the hood, **mem0 is wired to a local [Qdrant](https://qdrant.tech)
instance** running entirely on disk in `pessoa_qdrant/` (no Qdrant server
process — the embedded mode). Embeddings have dimension 768 to match
`nomic-embed-text`. Nothing ever leaves the machine. Memory persists across
restarts, and the HTTP API and the MCP server share the same store as the
Streamlit UI.

## Performance notes

- Smaller `NUM_CTX` → faster prompt evaluation and a lighter KV cache.
- Background, `infer=False` memory writes keep the model free for your next prompt.
- If the *first* prompt after startup is slow, that's the model loading into
  memory; later prompts reuse it (kept warm by `KEEP_ALIVE`).

## License

Apache License 2.0. See [LICENSE](LICENSE).
