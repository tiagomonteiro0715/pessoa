# Pessoa: Local, LLM Agnostic AI Agent Infrastructure

![Pessoa Logo](/logo_compressed.png)

<p align="center">
  <img src="https://img.shields.io/github/license/tiagomonteiro0715/pessoa" alt="License"/>
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python 3.12+"/>
  <img src="https://img.shields.io/github/last-commit/tiagomonteiro0715/pessoa" alt="Last Commit"/>
  <img src="https://img.shields.io/github/stars/tiagomonteiro0715/pessoa" alt="Stars"/>
  <img src="https://img.shields.io/github/forks/tiagomonteiro0715/pessoa" alt="Forks"/>
</p>

## Project Demo




https://github.com/user-attachments/assets/578a01c2-3cbe-42d1-b85d-b348e144cd90



-------


Over many decades, computing grew from silicon chips to PCs and then to the internet.

I arrived in the San Francisco Bay Area in august 2025. Now, in mid-2026, we are witnessing the next shift in AI!

A lot of AI is moving from LLMs to agentic infrastructure. From research side, world models are becoming more popular and physical AI will likely come next!

It is crucial for Portugal and the EU to show initiative with their own LLMs. However, they should be pragmatic.

The main criticism of the EU is its excess of regulation. While the US and China innovate, the EU regulates.

Instead of waiting for a sovereign European foundation model, the EU can achieve data privacy and great performance by wrapping open-source models (like Gemma4) in local infrastructure.

Pessoa is a blueprint(less than 1200 lines of python code) for this pragmatic approach.

It uses Gemma 4 (can be changed for any other LLM), a memory layer and system prompts (currently only a Portuguese one) to enforce outputs in a given language.

This way, by the LLM knowing English as its foundational language, it can interact with the web and other services via APIs and MCPs. Something a non-English LLM will likely have difficulty with.

## Table of contents

- [Why is this project called "Pessoa"?](#why-is-this-project-called-pessoa)
- [How can I use this project?](#how-can-i-use-this-project)
- [Stack, Architecture and Project tree](#stack)
- [Run](#run)
- [Configuration](#configuration)
- [Using Claude Skills as personas](#using-claude-skills-as-personas)
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
  client (Claude Desktop, etc.) can call.

## Stack, Architecture and Project tree

This project is an system with a modular architecture. For this reason, it has few API endpoints and a Streamlit frontend as an LLM interface.

Also, with pyproject.toml and uv, it is very easy to install all needed libraries.

The memory layer (mem0 + qdrant) is decoupled from the inference engine. So if you want to switch Ollama for vLLM or anything else, you can easily!

Finally, it runs 100% locally, and it uses FastAPI and FastMCP to allow integrations with other services and tools.

In the end, the streamlit is just a basic playground and the most comporant components are the memory layer sepeareted from the API and MCP.

#### Project tree

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


## Run

#### Install dependencies


This project uses uv to manage all python dependencies. So the first step is [having uv installed in your computer](https://docs.astral.sh/uv/).

In addition it uses ollama as the inference engine and this way [ollama is needed to be installed as well](https://ollama.com/).

First step is just to get the code in your local directory
```bash
git clone https://github.com/tiagomonteiro0715/pessoa
cd pessoa
```

From there, to ensure no depencies problem, you can pin python 3.12, 3.13 or 3.14. 

Below I show how to install and use python version 3.13
```bash
uv python install 3.13
uv python pin 3.13
```

Finally, with just two words we get all the python libraries to run the project!

```bash
uv sync
```

#### Launch the Streamlit UI (the usual way)

```bash
ollama serve (In an seperate terminal)
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

Claude Skills are nothing more than text instructions for
an LLM. Pessoa already builds its system prompt as a stack of
`{"role": "system", "content": …}` blocks (the pt-PT persona, recalled memory,
optional web/weather facts). This way, a skill slots into that stack as one more
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

## Contributing

This project is a working template — improvements and corrections are welcome.

- **Found a bug, or noticed something off about the pt-PT prompt?** Open an issue or email me.
- **Have a skill file worth shipping with the repo?** Drop it under `skills/` and open a PR.
- **Tested on a Python version, alternative backend (vLLM, llama.cpp, …), or model not currently listed?** Let me know — I want to keep the model-agnostic / version-agnostic claims honest.

Reach out at monteiro.t@northeastern.edu or via GitHub issues.

## Built With

- [uv](https://github.com/astral-sh/uv) — dependency management + lockfile
- [Ollama](https://ollama.com) — local LLM inference (default: `gemma4:e2b`)
- [mem0](https://github.com/mem0ai/mem0) — long-term memory layer
- [Qdrant](https://qdrant.tech) — on-disk vector store (embedded mode)
- [Streamlit](https://streamlit.io) — chat UI
- [FastAPI](https://fastapi.tiangolo.com) — OpenAPI 3.0 HTTP wrapper
- [mcp Python SDK / FastMCP](https://github.com/modelcontextprotocol/python-sdk) — Model Context Protocol server over stdio
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
