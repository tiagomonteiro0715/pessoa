# Pessoa: Local, LLM Agnostic AI Agent Infrastructure

![Pessoa Logo](/logo_compressed.png)

<p align="center">
  <img src="https://img.shields.io/github/license/tiagomonteiro0715/pessoa" alt="License"/>
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python 3.12+"/>
  <img src="https://img.shields.io/github/last-commit/tiagomonteiro0715/pessoa" alt="Last Commit"/>
  <img src="https://img.shields.io/github/stars/tiagomonteiro0715/pessoa" alt="Stars"/>
  <img src="https://img.shields.io/github/forks/tiagomonteiro0715/pessoa" alt="Forks"/>
</p>

Over many decades, computing grew from silicon chips to PCs and then to the internet.

I arrived in the San Francisco Bay Area in august 2025. Now, in mid-2026, we are witnessing the next shift in AI!

A lot of AI is moving from LLMs to agentic infrastructure. From research side, world models are becoming more popular and physical AI will likely come next afer or during AI!

It is crucial for Portugal and the EU to show initiative with their own LLMs. However, they should be pragmatic.

The main criticism of the EU is its excess of regulation. While the US and China innovate, the EU regulates.

Instead of waiting for a sovereign European foundation model, the EU can achieve data privacy and great performance by wrapping open-source models (like Gemma4) in local infrastructure.

Pessoa is a blueprint for this pragmatic approach.

It uses Gemma 4 (can be changed for any other LLM) while using system prompts (currently only Portuguese ones) to enforce outputs in a given language.

This way, by the LLM knowing English as its foundational language, it can interact with the web and other services via APIs and MCPs. Something a non-English LLM will likely have difficulty with.

### The Stack & Architecture

This project is an architectural template. For this reason, it has few API endpoints and a Streamlit frontend as an LLM interface.

Also, with pyproject.toml and uv, it is very easy to install all needed libraries.

The memory layer (mem0 + qdrant) is decoupled from the inference engine. So if you want to switch Ollama for vLLM or anything else, you can easily!

Finally, it runs 100% locally, and it uses FastAPI and FastMCP to allow integrations with other services and tools.

### Project tree

```text
pessoa/
├── README.md
├── LICENSE
├── pyproject.toml          # uv-locked Python dependencies
├── main.py                 # launcher: --skill flag, Ollama bootstrap, runs Streamlit
├── tox.ini                 # tox sessions — Python-version matrix
├── noxfile.py              # nox sessions — per-test-layer (contract / e2e / limits / mcp)
├── src/
│   ├── chat.py             # engine: model config, memory, streaming, skill composition
│   ├── system_prompt.py    # base pt-PT persona
│   ├── app.py              # Streamlit chat UI
│   ├── styles.css          # dark theme + sidebar styling
│   ├── API/
│   │   └── server.py       # FastAPI / OpenAPI HTTP wrapper
│   └── MCP/
│       └── server.py       # MCP server over stdio (chat, search_memory tools)
├── skills/
│   └── code-reviewer.md    # example Claude Skill (pt-PT)
├── tests/
│   ├── test_api_contract.py   # schema + endpoints, no LLM
│   ├── test_api_e2e.py        # real generation against Ollama
│   ├── test_api_limits.py     # concurrency sweep (needs server running)
│   └── test_mcp.py            # MCP tool list + invocations
└── pessoa_qdrant/          # local Qdrant vector store (runtime data)
```

## Table of contents

- [Why is this project called "Pessoa"?](#why-is-this-project-called-pessoa)
- [How can I use this project?](#how-can-i-use-this-project)
- [Requirements](#requirements)
- [Run](#run)
- [Project structure](#project-structure)
- [Configuration](#configuration)
- [Using Claude Skills as personas](#using-claude-skills-as-personas)
- [How memory works](#how-memory-works)
- [Performance notes](#performance-notes)
- [Contributing](#contributing)
- [Built With](#built-with)
- [Contact](#contact)
- [License](#license)

## Why is this project called "Pessoa"?

![image of fernando pessoa](https://github.com/tiagomonteiro0715/pessoa/blob/main/fernando.jpg)

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
- **Python 3.12, 3.13, or 3.14.** Tested on all three via the `tox` matrix
  (see [Run the tests](#run-the-tests) below). Python 3.15 currently fails
  because `lxml` lacks prebuilt wheels for it. On Linux / macOS, lock the
  project to a known-good interpreter to avoid resolver surprises:

  ```bash
  uv python pin 3.13
  ```

  That writes a `.python-version` file so every `uv run …` uses 3.13.

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

> **Linux + systemd Ollama**: the launcher detects this and prints the manual
> env-var edits you'd need (`OLLAMA_FLASH_ATTENTION=1`,
> `OLLAMA_KV_CACHE_TYPE=q4_0`, `OLLAMA_KEEP_ALIVE=45m`) under
> `sudo systemctl edit ollama.service`. Applying them is a one-time perf win;
> skipping is harmless — everything still works without them.

> **First-run download**: the first time mem0's NLP backend kicks in, it pulls
> the spaCy `en_core_web_sm` model (~13 MB). Subsequent runs reuse it.

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

#### Run the tests

On Ubuntu, the sequence I used to exercise the matrix + the four test layers end-to-end:

```bash
uv sync                       # installs deps, including tox + nox

# Make the Python interpreters tox will sweep actually available.
uv python install 3.12
uv python install 3.13
uv python install 3.14
uv python install 3.15        # optional — currently fails on lxml; see Requirements

# Multi-Python matrix (contract tests only).
uv run tox

# Per-layer sessions on Python 3.12.
nox -s contract               # fast, no real inference
nox -s api_e2e                # slow, real LLM
nox -s mcp                    # slow, spawns the MCP server; real LLM

# For the limits session, the API must be running externally:
uv run python src/API/server.py     # terminal 1
nox -s api_limits                   # terminal 2
```

See [`tox.ini`](tox.ini) and [`noxfile.py`](noxfile.py) for how the
environments and sessions are wired.

#### Results

The sequence above was run on Ubuntu / i7-6500U (CPU only, no GPU):

**tox matrix (contract tests across Python versions):**

| Env | Status | Time | Notes |
|---|---|---|---|
| `py311` | SKIP | 1.4s | Interpreter not installed |
| `py312` | ✓ | 9m 41s | First-run cost: pulled `gemma4:e2b` from Ollama during `ensure_model_pulled()` |
| `py313` | ✓ | 1m 16s | Model already cached |
| `py314` | ✓ | 1m 12s | Model already cached |
| `py315` | ✗ | 7.7s | `lxml` build fails — no prebuilt wheels for py315 yet |

**nox sessions (per-test-layer, all on Python 3.12):**

| Session | Status | Tests | Time |
|---|---|---|---|
| `contract` | ✓ | 6 / 6 | ~1 min (mostly venv create + dep install) |
| `api_e2e` | ✓ | 4 / 4 | 49s |
| `mcp` | ✓ | 5 / 5 | 28s |
| `api_limits` | ✓ | 3 / 3 | 31s |

See [Performance notes](#performance-notes) for the actual latency numbers
produced by the `api_limits` session.

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

## Using Claude Skills as personas

Claude Skills — the markdown-with-YAML-frontmatter format the Claude Code CLI
ships its built-in personas in — are nothing more than text instructions for
the model. Pessoa already builds its system prompt as a stack of
`{"role": "system", "content": …}` blocks (the pt-PT persona, recalled memory,
optional web/weather facts), so a skill slots into that stack as one more
block.

> **Status:** implemented. Drop a markdown file under `skills/` (one example
> ships with the repo: [`skills/code-reviewer.md`](skills/code-reviewer.md))
> and pass `--skill <name>` to `main.py`.

### Skill file format

A skill is one markdown file. The frontmatter (`name`, `description`) is
metadata for tooling; the body is what the model actually reads.

````markdown
---
name: code-reviewer
description: Reviews code for bugs and clarity, replies in pt-PT.
---

És um revisor de código experiente. Quando o utilizador colar código:

- Identifica bugs concretos (não estilo).
- Sugere apenas alterações com impacto real.
- Cita o ficheiro:linha quando for visível.
- Responde sempre em português de Portugal.
````

### Intended invocation

Drop the file into `skills/` and launch by name:

```bash
python main.py --skill code-reviewer
```

Or point at any absolute path:

```bash
python main.py --skill /any/path/to/foo.md
```

By default the skill body is **appended** to Pessoa's base pt-PT persona —
the language and safety rules stay, the skill adds specialization on top.
Pass `--skill-mode replace` for full persona replacement (advanced: your
skill then owns the language and safety rules).

### How it wires in

The plumbing is one environment variable (`PESSOA_SKILL=<absolute-path>`,
plus `PESSOA_SKILL_MODE=append|replace`) set by `main.py` *before* launching
the Streamlit / API / MCP subprocess. `chat.py` reads it at module import,
strips the YAML frontmatter (a five-line hand-rolled parser, no `pyyaml`
dependency), and composes `ACTIVE_SYSTEM_PROMPT` accordingly — that's what
`stream_answer` then uses as its first system message. The API and MCP entry
points pick the env var up automatically: launch them with `PESSOA_SKILL=…`
set in the parent shell and they inherit the persona for free.

The router pattern Pessoa already uses for long-term memory (`mem.search` over
the user's prompt → top-k results injected into the messages list) could be
repurposed to surface a skill *on demand* instead of selecting one at launch —
that's the natural next step if you wanted Pessoa to behave more like Claude
Code's harness, picking skills automatically by description match rather than
by an explicit flag.

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

Measured on an HP EliteBook 840 G3 (i7-6500U, CPU only, no GPU) running
Ubuntu with Ollama under systemd:

- **Baseline:** one short `/chat` request → about **3-5 seconds** end-to-end.
- **Concurrency** — Ollama overlaps requests partially (not pure
  serialization). Wall-clock observed via `nox -s api_limits`:
  - `N=2` concurrent → 6.5s total (avg 5.1s per request)
  - `N=4` concurrent → 12.7s total (avg 8.5s per request)
- **`/health` under load** — stayed at ~5 ms while `/chat` was busy. No
  accidental global lock in the API path.
- **First prompt is slowest** — that's the model loading into memory; later
  prompts reuse the warm model via `KEEP_ALIVE`.
- Smaller `NUM_CTX` → faster prompt evaluation and a lighter KV cache.
- Background, `infer=False` memory writes keep the model free for your next prompt.

## Contributing

This project is a working template — improvements and corrections are welcome.

- **Found a bug, or noticed something off about the pt-PT prompt?** Open an issue or email me.
- **Have a skill file worth shipping with the repo?** Drop it under `skills/` and open a PR.
- **Tested on a Python version, alternative backend (vLLM, llama.cpp, …), or model not currently listed?** Let me know — I want to keep the model-agnostic / version-agnostic claims honest.

Reach out at monteiro.t@northeastern.edu or via GitHub issues.

## Built With

- [Ollama](https://ollama.com) — local LLM inference (default: `gemma4:e2b`)
- [mem0](https://github.com/mem0ai/mem0) — long-term memory layer
- [Qdrant](https://qdrant.tech) — on-disk vector store (embedded mode)
- [Streamlit](https://streamlit.io) — chat UI
- [FastAPI](https://fastapi.tiangolo.com) — OpenAPI 3.0 HTTP wrapper
- [mcp Python SDK / FastMCP](https://github.com/modelcontextprotocol/python-sdk) — Model Context Protocol server over stdio
- [uv](https://github.com/astral-sh/uv) — dependency management + lockfile
- [tox](https://tox.wiki) / [nox](https://nox.thea.codes) — multi-environment test orchestration

## Contact

**Tiago Monteiro**

- Email: monteiro.t@northeastern.edu
- GitHub: [@tiagomonteiro0715](https://github.com/tiagomonteiro0715)
- FreeCodeCamp: [Author profile](https://www.freecodecamp.org/news/author/tiagomonteiro)

## License

Apache License 2.0. See [LICENSE](LICENSE).

---

<p align="center">
  If this template helped you ship a local agent stack, please star the repo.<br>
  It helps others find it.
</p>
