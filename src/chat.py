"""Shared chat + setup logic for the Pessoa assistant.

Used by both the CLI (main.py) and the Streamlit UI (src/app.py).
"""
import asyncio
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import ollama
from mem0 import Memory

from system_prompt import SYSTEM_PROMPT

MODEL = "gemma4:e2b"
EMBED_MODEL = "nomic-embed-text"
NUM_CTX = 8192  # Big enough to fit an image/audio attachment + a real turn.
KEEP_ALIVE = "45m"
USER_ID = "pessoa"

# Memory-consolidation worker: raw chat snippets persisted with infer=False
# are periodically distilled into facts via mem0's LLM extraction. Tunables:
CONSOLIDATE_EVERY = 600        # seconds — interval between consolidation passes
CONSOLIDATE_AFTER = 300        # only fold raw memories older than this
CONSOLIDATE_MIN_BATCH = 6      # skip the cycle if fewer raws are pending

# Persistent on-disk location for the vector store so memory survives restarts
# (/tmp is wiped on reboot). Lives next to the project root.
QDRANT_PATH = str(Path(__file__).resolve().parent.parent / "pessoa_qdrant")

SERVER_ENV = {
    "OLLAMA_FLASH_ATTENTION": "1",
    "OLLAMA_KV_CACHE_TYPE": "q4_0",
    "OLLAMA_KEEP_ALIVE": KEEP_ALIVE,
}



STOP = ["<|eot_id|>", "<|start_header_id|>", "<|end_header_id|>"]

# Set by stream_answer() while a user request is in flight, so the async
# consolidator skips its cycle and doesn't queue ahead of the user's prompt.
_chat_busy = threading.Event()
_consolidator_started = False


def build_memory() -> Memory:
    """Create the mem0 store. Kept as a function so callers (e.g. Streamlit)
    can cache the instance instead of building it at import time."""
    mem = Memory.from_config({
        "llm": {"provider": "ollama", "config": {"model": MODEL}},
        "embedder": {"provider": "ollama", "config": {"model": EMBED_MODEL}},
        "vector_store": {"provider": "qdrant", "config": {
            "path": QDRANT_PATH, "embedding_model_dims": 768}},
    })
    _ensure_consolidator(mem)
    return mem


def _ensure_consolidator(mem: Memory) -> None:
    """Spin up the asyncio consolidation worker once per process."""
    global _consolidator_started
    if _consolidator_started:
        return
    _consolidator_started = True

    def _runner():
        try:
            asyncio.run(_consolidate_loop(mem))
        except Exception as e:
            print(f"[pessoa] consolidator died: {e}", flush=True)

    threading.Thread(target=_runner, daemon=True).start()


async def _consolidate_loop(mem: Memory) -> None:
    """Periodically distil raw chat snippets into facts when the system is idle."""
    while True:
        await asyncio.sleep(CONSOLIDATE_EVERY)
        if _chat_busy.is_set():
            continue
        try:
            await asyncio.to_thread(_consolidate_once, mem)
        except Exception as e:
            print(f"[pessoa] consolidate pass failed: {e}", flush=True)


def _consolidate_once(mem: Memory) -> None:
    """Gather raw memories older than CONSOLIDATE_AFTER, re-add them with
    infer=True so mem0's LLM extracts compact facts, then drop the originals."""
    now = time.time()
    items = mem.get_all(user_id=USER_ID).get("results", [])
    raws = [
        m for m in items
        if (m.get("metadata") or {}).get("raw")
        and now - (m.get("metadata") or {}).get("ts", 0) > CONSOLIDATE_AFTER
    ]
    if len(raws) < CONSOLIDATE_MIN_BATCH:
        return
    raws.sort(key=lambda m: (m.get("metadata") or {}).get("ts", 0))
    transcript = "\n".join(f"- {m['memory']}" for m in raws)
    mem.add(
        [{"role": "user",
          "content": ("Excertos de conversas anteriores. Extrai factos "
                      "compactos e úteis sobre o utilizador:\n\n" + transcript)}],
        user_id=USER_ID,
        infer=True,
    )
    for m in raws:
        try:
            mem.delete(memory_id=m["id"])
        except Exception:
            pass
    print(f"[pessoa] consolidated {len(raws)} raw memories → facts", flush=True)


def ensure_server_env():
    """Apply Ollama optimization env vars and restart the server if missing.

    Why: OLLAMA_FLASH_ATTENTION and OLLAMA_KV_CACHE_TYPE are read by the Ollama
    server at startup. Setting them in this process alone wouldn't reach the
    already-running daemon, so the daemon has to be bounced with the vars in its
    own environment. How that's done is platform-specific.
    """
    missing = {k: v for k, v in SERVER_ENV.items() if os.environ.get(k) != v}
    if not missing:
        return False

    for k, v in missing.items():
        os.environ[k] = v

    if sys.platform == "win32":
        _restart_ollama_windows(missing)
    else:
        _restart_ollama_posix(missing)
    return True


def _restart_ollama_windows(missing: dict):
    for k, v in missing.items():
        print(f"setx {k}={v}")
        subprocess.run(["setx", k, v], check=True, capture_output=True)

    print("Restarting Ollama so new env vars take effect...")
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process ollama,'ollama app' -ErrorAction SilentlyContinue | Stop-Process -Force"],
        capture_output=True,
    )
    time.sleep(2)
    app_exe = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Ollama" / "ollama app.exe"
    subprocess.Popen([str(app_exe)], creationflags=subprocess.DETACHED_PROCESS)
    time.sleep(4)


def _restart_ollama_posix(missing: dict):
    # If Ollama runs under systemd, the env vars must live in a service drop-in;
    # restarting `ollama serve` with our os.environ wouldn't touch the daemon.
    if _ollama_is_systemd():
        print("Ollama runs under systemd. Persist the optimization vars with:")
        print("  sudo systemctl edit ollama.service")
        print("Add under [Service]:")
        for k, v in SERVER_ENV.items():
            print(f'  Environment="{k}={v}"')
        print("Then: sudo systemctl daemon-reload && sudo systemctl restart ollama")
        return

    # Otherwise assume a user-launched `ollama serve`: kill it and relaunch with
    # the new env (inherited from this process's os.environ).
    print("Restarting `ollama serve` so new env vars take effect...")
    subprocess.run(["pkill", "-f", "ollama serve"], capture_output=True)
    time.sleep(2)
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    time.sleep(4)


def _ollama_is_systemd() -> bool:
    if not shutil.which("systemctl"):
        return False
    result = subprocess.run(
        ["systemctl", "is-active", "ollama"], capture_output=True, text=True
    )
    return result.stdout.strip() in ("active", "activating")


def ensure_model_pulled():
    installed = {m.model for m in ollama.list().models}
    for model in (MODEL, EMBED_MODEL):
        print(f"Ensuring model '{model}' is available...")
        if not any(m == model or m.startswith(f"{model}:") for m in installed):
            print(f"Pulling {model}...")
            ollama.pull(model)
        else:
            print(f"{model} already installed.")


def _ddgs():
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
    return DDGS()


def web_search(query: str, text_n: int = 8, news_n: int = 5) -> str:
    """DuckDuckGo text + news hits as a bulleted block. '' on failure."""
    try:
        d = _ddgs()
        text_hits = list(d.text(query, max_results=text_n)) or []
        try:
            news_hits = list(d.news(query, max_results=news_n)) or []
        except Exception:
            news_hits = []
        print(f"[pessoa] web_search '{query}' → "
              f"{len(text_hits)} text, {len(news_hits)} news", flush=True)
        lines = []
        for h in text_hits:
            lines.append(f"- {h.get('title','')}: {h.get('body','')} "
                         f"({h.get('href','')})")
        for h in news_hits:
            lines.append(f"- [notícia {h.get('date','')}] {h.get('title','')}: "
                         f"{h.get('body','')} ({h.get('url') or h.get('href','')})")
        return "\n".join(lines)
    except Exception as e:
        print(f"[pessoa] web_search FAILED: {e}", flush=True)
        return ""


_WEATHER_RE = re.compile(
    r"(?:tempo|clima|previs[ãa]o|weather|forecast)\s+"
    r"(?:de|em|in|no|na|para|of|do|da)\s+"
    r"([\wÀ-ÿ][\wÀ-ÿ\s\-\.']{1,40}?)"
    r"(?=\?|$|\.|,|!|;| hoje| amanh| amanhã| tomorrow| today)",
    re.IGNORECASE,
)


def _weather_location(prompt: str) -> str | None:
    m = _WEATHER_RE.search(prompt)
    return m.group(1).strip() if m else None


def weather_lookup(location: str) -> str:
    """Live current+3-day forecast from wttr.in. '' on failure."""
    try:
        import httpx
        r = httpx.get(f"https://wttr.in/{location}", params={"format": "j1"},
                      timeout=5.0, headers={"User-Agent": "pessoa/0.1"})
        r.raise_for_status()
        j = r.json()
        now = j["current_condition"][0]
        area = (j.get("nearest_area") or [{}])[0]
        place = area.get("areaName", [{}])[0].get("value", location)
        country = area.get("country", [{}])[0].get("value", "")
        lines = [
            f"Local: {place}, {country}",
            f"Agora: {now['weatherDesc'][0]['value']}, {now['temp_C']}°C "
            f"(sente-se {now['FeelsLikeC']}°C), vento {now['windspeedKmph']} km/h, "
            f"humidade {now['humidity']}%",
        ]
        for d in j.get("weather", [])[:3]:
            mid = d["hourly"][4] if len(d.get("hourly", [])) > 4 else {}
            lines.append(
                f"{d['date']}: {d['mintempC']}°C a {d['maxtempC']}°C, "
                f"meio-dia: {mid.get('weatherDesc',[{'value':'?'}])[0]['value']}"
            )
        print(f"[pessoa] weather '{location}' → ok", flush=True)
        return "\n".join(lines)
    except Exception as e:
        print(f"[pessoa] weather '{location}' FAILED: {e}", flush=True)
        return ""


def stream_answer(
    mem: Memory,
    prompt: str,
    images: list | None = None,
    audios: list | None = None,
    use_web: bool = False,
):
    """Yield response chunks for `prompt`, enriched with relevant memory.

    `images` / `audios` attach to the user turn for multimodal models.
    `use_web` runs a live DuckDuckGo search and injects the top hits.
    """
    related = mem.search(prompt, filters={"user_id": USER_ID}, top_k=3).get("results", [])
    context = "\n".join(f"- {m['memory']}" for m in related)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        messages.append({
            "role": "system",
            "content": f"Memória relevante de conversas anteriores:\n{context}",
        })
    if use_web:
        blocks = []
        loc = _weather_location(prompt)
        if loc:
            w = weather_lookup(loc)
            if w:
                blocks.append(
                    "DADOS METEOROLÓGICOS EM TEMPO REAL (wttr.in):\n" + w
                )
        web = web_search(prompt)
        if web:
            blocks.append("RESULTADOS DE PESQUISA WEB (DuckDuckGo):\n" + web)
        if blocks:
            messages.append({
                "role": "system",
                "content": (
                    "FACTOS EM TEMPO REAL — tenho neste momento acesso aos "
                    "seguintes dados, obtidos agora da internet. São factos "
                    "atuais e fiáveis; usa-os para responder à pergunta do "
                    "utilizador na primeira pessoa, citando valores concretos "
                    "(temperatura, datas, números, fontes). Nunca digas que "
                    "não tens acesso à internet — tenho, e os dados estão "
                    "aqui:\n\n" + "\n\n".join(blocks)
                ),
            })
        else:
            messages.append({
                "role": "system",
                "content": (
                    "Tentei pesquisar na internet mas não obtive resultados. "
                    "Avisa o utilizador disso e responde com base no que sabes."
                ),
            })
    user_turn = {"role": "user", "content": prompt}
    modalities = []
    # ollama-python is most reliable when fed image *paths*; in-memory bytes
    # can be silently dropped or misclassified depending on client version.
    # Spool to temp files for the duration of the call, then unlink.
    tmp_paths: list[Path] = []
    if images:
        for i, b in enumerate(images):
            p = Path(tempfile.mkstemp(prefix=f"pessoa_img_{i}_", suffix=".bin")[1])
            p.write_bytes(b)
            tmp_paths.append(p)
        user_turn["images"] = [str(p) for p in tmp_paths]
        modalities.append("imagem(s)")
        print(f"[pessoa] sending {len(images)} image(s) via "
              f"{[str(p) for p in tmp_paths]}", flush=True)
    if audios:
        audio_paths = []
        for i, b in enumerate(audios):
            p = Path(tempfile.mkstemp(prefix=f"pessoa_aud_{i}_", suffix=".bin")[1])
            p.write_bytes(b)
            tmp_paths.append(p)
            audio_paths.append(str(p))
        user_turn["audios"] = audio_paths
        modalities.append("áudio(s)")
        print(f"[pessoa] sending {len(audios)} audio(s) via {audio_paths}", flush=True)

    if modalities:
        messages.insert(1, {
            "role": "system",
            "content": (
                f"O utilizador anexou {' e '.join(modalities)} a esta mensagem. "
                "Se conseguires mesmo ver/ouvir o conteúdo, descreve-o com "
                "precisão e responde com base nele. Se NÃO conseguires aceder "
                "ao conteúdo anexado, diz-o claramente — não inventes nem "
                "adivinhes o que lá está."
            ),
        })
    messages.append(user_turn)

    answer = ""
    _chat_busy.set()
    try:
        stream = ollama.chat(
            model=MODEL,
            messages=messages,
            think=False,
            keep_alive=KEEP_ALIVE,
            options={"num_ctx": NUM_CTX, "stop": STOP},
            stream=True,
        )
        for chunk in stream:
            piece = chunk.message.content
            answer += piece
            yield piece
    finally:
        for p in tmp_paths:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        _chat_busy.clear()

    # Persist the exchange in the background. infer=False stores the raw turns
    # as memory WITHOUT mem0's LLM fact-extraction step — that extraction is a
    # full model generation, and since Ollama serves one request at a time per
    # model, it would otherwise queue ahead of the user's next prompt (making
    # every prompt after the first feel slow). We only pay an embed + write here.
    # Best-effort — a failed memory write must not crash the chat.
    def _store():
        try:
            mem.add(
                [{"role": "user", "content": prompt},
                 {"role": "assistant", "content": answer}],
                user_id=USER_ID,
                infer=False,
                metadata={"raw": True, "ts": time.time()},
            )
        except Exception:
            pass

    threading.Thread(target=_store, daemon=True).start()
