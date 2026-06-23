# Pessoa


Fernando António Nogueira de Seabra Pessoa (/pɛˈsoʊə/;[1] Portuguese: [fɨɾˈnɐ̃du pɨˈsoɐ]; 13 June 1888–30 November 1935) was a Portuguese poet, writer, literary critic, translator, and publisher. He has been described as one of the most significant literary figures of the 20th century and one of the greatest poets in the Portuguese literature. He also wrote in and translated from English and French.

Pessoa was a prolific writer both in his own name and approximately seventy-five other names, of which three stand out: Alberto Caeiro, Álvaro de Campos, and Ricardo Reis. He did not define these as pseudonyms because he felt that this did not capture their true independent intellectual life and instead called them heteronyms, a term he invented.[2] These imaginary figures sometimes held unpopular or extreme views.

A local, ChatGPT-style assistant that speaks **Português de Portugal (pt-PT)** and
remembers past conversations. Everything runs on your machine — the model via
[Ollama](https://ollama.com), long-term memory via [mem0](https://github.com/mem0ai/mem0)
backed by a local [Qdrant](https://qdrant.tech) store. No cloud, no API keys.

## What it does

- **Chat UI** (Streamlit): multi-chat sidebar (new / select / delete), streaming
  answers, a *Parar geração* (stop) button, and an animated typing indicator.
- **Long-term memory**: relevant snippets from earlier chats are recalled and fed
  to the model, so the assistant "remembers" you across sessions.
- **Always answers in pt-PT** (unless you explicitly ask for another language),
  with a tuned system prompt covering tone, formatting and prompt-injection
  defences.
- **CLI batch runner** (`main.py`): runs a fixed list of prompts through the same
  chat logic — handy for smoke-testing the model and memory.

## Requirements

- [Ollama](https://ollama.com) installed and running.
- [uv](https://github.com/astral-sh/uv) for dependency management.
- The models are pulled automatically on first CLI run; for the UI, pull them once:

  ```bash
  ollama pull gemma4:e4b
  ollama pull nomic-embed-text
  ```

## Run

**Web UI:**


```bash
uv init
```

```bash
uv sync
```

```bash
uv run streamlit run src/app.py
```

Then open http://localhost:8501.

**CLI batch runner:**

```bash
uv run python main.py
```

## Project structure

| File | Purpose |
|------|---------|
| `src/app.py` | Streamlit chat UI (layout, theme, multi-chat state, streaming). |
| `src/chat.py` | Shared logic: model config, system prompt, memory, Ollama setup. |
| `main.py` | CLI batch runner over a fixed set of prompts. |
| `.streamlit/config.toml` | Streamlit dark theme. |
| `pessoa_qdrant/` | On-disk vector store (persists memory across restarts). |

## Configuration

Tunables live at the top of `src/chat.py`:

| Setting | Default | Notes |
|---------|---------|-------|
| `MODEL` | `gemma4:e4b` | Chat model. |
| `EMBED_MODEL` | `nomic-embed-text` | Embeddings for memory search. |
| `NUM_CTX` | `1024` | Context window. Larger = more context but slower / heavier. |
| `KEEP_ALIVE` | `45m` | How long Ollama keeps the model warm in memory. |
| `SYSTEM_PROMPT` | pt-PT prompt | Persona, language rules, safety, formatting. |
| `STOP` | Llama stop tokens | No-op for gemma; adjust if you switch model family. |

The system also sets Ollama optimization env vars (`OLLAMA_FLASH_ATTENTION`,
`OLLAMA_KV_CACHE_TYPE=q4_0`, `OLLAMA_KEEP_ALIVE`) for faster inference.

## How memory works

1. On each prompt, the top relevant memories are retrieved (`mem.search`) and added
   to the model's context as *"Memória relevante"*.
2. After the answer streams, the exchange is stored **in the background** with
   `infer=False` — it's saved as a raw snippet without an extra LLM extraction
   pass, so storing memory never blocks (or competes with) your next prompt.

Memory persists on disk in `pessoa_qdrant/`, so it survives restarts.

## Performance notes

- Smaller `NUM_CTX` → faster prompt evaluation and a lighter KV cache.
- Background, `infer=False` memory writes keep the model free for your next prompt.
- If the *first* prompt after startup is slow, that's the model loading into
  memory; later prompts reuse it (kept warm by `KEEP_ALIVE`).
