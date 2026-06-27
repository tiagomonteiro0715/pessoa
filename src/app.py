"""ChatGPT-like Streamlit interface for the Pessoa assistant.

Run with:  uv run streamlit run src/app.py
Assumes Ollama is already running and the models are pulled.
"""
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Thread

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Make `chat` importable whether run as `streamlit run src/app.py` (script dir
# on sys.path) or from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chat  # noqa: E402

st.set_page_config(page_title=f"pessoa: runs on {chat.MODEL}", layout="centered")

# Dark, professional theme (ChatGPT/Claude-like) over a muted gradient in the
# colors of Portugal: deep green → gold → deep red.
_CSS = (Path(__file__).resolve().parent / "styles.css").read_text(encoding="utf-8")
st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


@st.cache_resource(show_spinner="A ligar à memória…")
def get_memory():
    """Build the mem0 store once per session and reuse it across reruns."""
    return chat.build_memory()


mem = get_memory()


# --- Background streaming ---------------------------------------------------
# The model is consumed in a daemon thread that writes tokens into a shared
# dict held in session_state. This is what lets the user submit a new prompt
# while a previous answer is still streaming: a Streamlit rerun kills the
# script execution but the thread keeps going. On the next rerun we see the
# in-flight stream and resume polling instead of starting a new one.
def _stream_worker(state, prompt, images, audios, use_web):
    try:
        for piece in chat.stream_answer(
            mem, prompt, images=images, audios=audios, use_web=use_web,
        ):
            if state.get("cancelled"):
                break
            state["text"] += piece
    except Exception as e:
        state["error"] = str(e)
    finally:
        state["done"] = True


def _start_stream(prompt, images, audios, target_idx, chat_id, use_web=False):
    state = {
        "text": "",
        "done": False,
        "error": None,
        "cancelled": False,
        "target_idx": target_idx,
        "chat_id": chat_id,
        "finalized": False,
    }
    st.session_state.stream = state
    t = Thread(
        target=_stream_worker,
        args=(state, prompt, images, audios, use_web),
        daemon=True,
    )
    add_script_run_ctx(t, get_script_run_ctx())
    t.start()
    return state


# --- Multi-chat state -------------------------------------------------------
# chats: {chat_id: {"title", "messages", "created_at"}}
def new_chat() -> int:
    cid = st.session_state.next_id
    st.session_state.next_id += 1
    st.session_state.chats[cid] = {
        "title": "Nova conversa",
        "messages": [],
        "created_at": time.time(),
    }
    st.session_state.current = cid
    st.session_state.just_created = True
    return cid


_DATE_GROUPS = ("Hoje", "Ontem", "Últimos 7 dias", "Últimos 30 dias", "Mais antigos")
_SHOW_LIMIT = 25


def _group_label(ts: float) -> str:
    delta = (datetime.now().date() - datetime.fromtimestamp(ts).date()).days
    if delta <= 0:
        return "Hoje"
    if delta == 1:
        return "Ontem"
    if delta < 7:
        return "Últimos 7 dias"
    if delta < 30:
        return "Últimos 30 dias"
    return "Mais antigos"


def _delete_chat(cid: int) -> None:
    del st.session_state.chats[cid]
    if not st.session_state.chats:
        new_chat()
    elif st.session_state.current == cid:
        st.session_state.current = next(reversed(st.session_state.chats))


def _commit_rename(cid: int) -> None:
    new = (st.session_state.get(f"rename_{cid}") or "").strip()
    if new:
        st.session_state.chats[cid]["title"] = new[:60]
    st.session_state.editing_cid = None


if "chats" not in st.session_state:
    st.session_state.chats = {}
    st.session_state.next_id = 1
    new_chat()
    st.session_state.just_created = False  # don't animate the initial chat


# --- Sidebar: create / select / delete chats --------------------------------
# One-shot animation flags: scope the keyframes to <body> by toggling a class.
anim_classes = []
if st.session_state.pop("just_created", False):
    anim_classes.append("pessoa-just-created")
if st.session_state.pop("just_named", False):
    anim_classes.append("pessoa-just-named")
if anim_classes:
    st.markdown(
        f"<script>document.body.classList.add({', '.join(repr(c) for c in anim_classes)});"
        f"setTimeout(() => document.body.classList.remove({', '.join(repr(c) for c in anim_classes)}), 800);"
        "</script>",
        unsafe_allow_html=True,
    )

# Chat currently being streamed (may differ from the active one if the user
# switched mid-stream). Used to mark its sidebar row.
_active_stream = st.session_state.get("stream")
_streaming_cid = (
    _active_stream.get("chat_id")
    if _active_stream and not _active_stream.get("finalized")
    else None
)

with st.sidebar:
    if st.button("Nova conversa", use_container_width=True, key="new_chat_btn"):
        new_chat()
        st.rerun()
    st.text_input(
        "search",
        placeholder="Pesquisar conversas…",
        label_visibility="collapsed",
        key="search_query",
    )

    query = (st.session_state.get("search_query") or "").lower().strip()
    filtered = [
        (cid, conv) for cid, conv in st.session_state.chats.items()
        if not query or query in (conv["title"] or "").lower()
    ]
    groups: dict[str, list] = {}
    for cid, conv in filtered:
        groups.setdefault(
            _group_label(conv.get("created_at", time.time())), []
        ).append((cid, conv))

    show_all = st.session_state.get("show_all_chats", False)
    shown = 0
    capped = False
    for label in _DATE_GROUPS:
        items = groups.get(label, [])
        if not items or capped:
            continue
        st.markdown(
            f'<div class="pessoa-group-label">{label}</div>',
            unsafe_allow_html=True,
        )
        for cid, conv in reversed(items):
            if not show_all and shown >= _SHOW_LIMIT:
                capped = True
                break
            shown += 1

            if st.session_state.get("editing_cid") == cid:
                st.text_input(
                    "rename",
                    value=conv["title"],
                    key=f"rename_{cid}",
                    label_visibility="collapsed",
                    on_change=_commit_rename,
                    args=(cid,),
                )
                continue

            sel_col, kebab_col = st.columns([5, 1])
            title = conv["title"] or "Nova conversa"
            if cid == _streaming_cid:
                title = "● " + title
            is_current = cid == st.session_state.current
            if sel_col.button(
                title,
                key=f"sel_{cid}",
                use_container_width=True,
                type="primary" if is_current else "secondary",
            ):
                st.session_state.current = cid
                st.rerun()
            with kebab_col.popover("⋯", use_container_width=True):
                if st.button("Renomear", key=f"ren_{cid}", use_container_width=True):
                    st.session_state.editing_cid = cid
                    st.rerun()
                if st.button("Eliminar", key=f"era_{cid}", use_container_width=True):
                    _delete_chat(cid)
                    st.rerun()

    if not show_all and len(filtered) > _SHOW_LIMIT:
        if st.button(
            f"Mostrar mais ({len(filtered) - _SHOW_LIMIT})",
            use_container_width=True,
            key="show_more",
        ):
            st.session_state.show_all_chats = True
            st.rerun()

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    st.toggle("🌐 Internet", key="use_web", help="Anexa resultados do DuckDuckGo ao prompt.")

    st.markdown(
        f"""
        <div class="pessoa-brand">
            <div class="name">pessoa</div>
            <div class="tag">runs on {chat.MODEL}</div>
            <a class="repo" href="https://github.com/tiagomonteiro0715/pessoa"
               target="_blank" rel="noopener noreferrer">
                <svg viewBox="0 0 16 16" width="12" height="12" fill="currentColor"
                     aria-hidden="true">
                    <path d="M8 0C3.58 0 0 3.58 0 8a8 8 0 0 0 5.47 7.59c.4.07.55-.17.55-.38
                             0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94
                             -.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21
                             1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95
                             0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82
                             a7.5 7.5 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12
                             .51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54
                             1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16
                             8c0-4.42-3.58-8-8-8z"/>
                </svg>
                <span>tiagomonteiro0715/pessoa</span>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --- Main: the active conversation ------------------------------------------
conv = st.session_state.chats[st.session_state.current]

# One-shot "submit burst": pop the gradient into fast-and-bright for ~1.6s
# right after the user presses enter, then let it ease back to its slow rhythm.
if st.session_state.pop("submit_pulse", False):
    st.markdown(
        "<script>"
        "document.body.classList.add('pessoa-pulse');"
        "setTimeout(() => document.body.classList.remove('pessoa-pulse'), 1600);"
        "</script>",
        unsafe_allow_html=True,
    )

# If a background stream finished (or was cancelled) since the last rerun,
# attach its text to the conversation it belonged to and clear the slot.
_stream = st.session_state.get("stream")
if _stream and _stream.get("done") and not _stream.get("finalized"):
    target_chat = st.session_state.chats.get(_stream["chat_id"])
    if target_chat:
        tidx = _stream["target_idx"]
        text = _stream.get("text", "")
        if _stream.get("error") and not text:
            text = f"⚠️ Error: {_stream['error']}"
        if _stream.get("cancelled") and text:
            text = text + " _(parado)_"
        # Guard against double-insertion if a quick rerun lands us here twice.
        already = (
            0 <= tidx < len(target_chat["messages"]) - 1
            and target_chat["messages"][tidx + 1]["role"] == "assistant"
        )
        if not already and 0 <= tidx < len(target_chat["messages"]):
            target_chat["messages"].insert(tidx + 1, {"role": "assistant", "content": text})
    _stream["finalized"] = True
    st.session_state.pop("stream", None)
    _stream = None

IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "gif"}
AUDIO_EXTS = {"mp3", "wav", "ogg", "m4a", "flac"}


def _ext(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def _pending_user_indices(messages: list) -> list[int]:
    """User-turn indices that still have no assistant reply immediately after."""
    return [
        i for i, m in enumerate(messages)
        if m["role"] == "user"
        and (i + 1 >= len(messages) or messages[i + 1]["role"] != "assistant")
    ]


def _render_message(msg: dict, *, queued: bool = False) -> None:
    with st.chat_message(msg["role"]):
        if queued:
            st.markdown(
                '<div class="pessoa-queued-tag">'
                'à espera que a resposta anterior termine'
                '</div>',
                unsafe_allow_html=True,
            )
        for att in msg.get("attachments", []):
            ext = _ext(att["name"])
            if ext in IMAGE_EXTS:
                st.image(att["data"], caption=att["name"], width="stretch")
            elif ext in AUDIO_EXTS:
                st.audio(att["data"])
                st.caption(f"🎵 {att['name']}")
            else:
                st.caption(f"📎 {att['name']}")
        if msg["content"]:
            st.markdown(msg["content"])


# "Generating" is derived from state: if any user turn has no reply, we're
# generating (or about to). This removes the need for a separate flag that
# could fall out of sync with the actual conversation.
pending = _pending_user_indices(conv["messages"])
streaming_idx = pending[0] if pending else None
queued_idxs = set(pending[1:])
split = streaming_idx + 1 if streaming_idx is not None else len(conv["messages"])
generating = streaming_idx is not None

for idx in range(split):
    _render_message(conv["messages"][idx])

# Empty-state welcome card: model capabilities, shown only before any turn.
if not conv["messages"] and not generating:
    st.markdown(
        f"""
        <div class="pessoa-welcome">
            <div class="pessoa-welcome-title">Capacidades do modelo</div>
            <div class="pessoa-welcome-row"><b>Modelo</b><span>{chat.MODEL} (multimodal)</span></div>
            <div class="pessoa-welcome-row"><b>Janela de contexto máxima</b><span>128K tokens</span></div>
            <div class="pessoa-welcome-row"><b>Janela em uso (inferência)</b><span>{chat.NUM_CTX:,} tokens. Reduzida para resposta mais rápida</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# New input -> store the user turn and flip into "generating" mode on a rerun,
# so the Stop button can be rendered alongside the streaming answer.
submitted = st.chat_input(
    "Escreve uma mensagem…",
    accept_file="multiple",
    file_type=sorted(IMAGE_EXTS | AUDIO_EXTS),
)
if submitted:
    text = submitted.text if hasattr(submitted, "text") else submitted
    files = submitted.files if hasattr(submitted, "files") else []
    attachments = [{"name": f.name, "data": f.getvalue()} for f in files]
    if text or attachments:
        conv["messages"].append({
            "role": "user",
            "content": text or "",
            "attachments": attachments,
            "use_web": st.session_state.get("use_web", False),
        })
        if conv["title"] == "Nova conversa":
            seed = text or (attachments[0]["name"] if attachments else "Nova conversa")
            conv["title"] = seed[:40] + ("…" if len(seed) > 40 else "")
            st.session_state.just_named = True
        st.session_state.submit_pulse = True
        st.rerun()

streaming_placeholder = None
if generating and streaming_idx is not None:
    # Declare the streaming bubble's placeholder NOW, in its natural place
    # in the render order, but with no content yet. We'll fill it from the
    # poll loop further down, after the queued bubbles have been rendered —
    # otherwise the loop's time.sleep blocks them from ever appearing.
    with st.chat_message("assistant"):
        streaming_placeholder = st.empty()
        # If we're resuming a stream that already accumulated tokens (a rerun
        # caused by the user submitting a new prompt mid-answer), paint what
        # we have right away to avoid a brief typing-dots flash.
        existing = _stream["text"] if _stream else ""
        if existing:
            streaming_placeholder.markdown(existing)
        else:
            streaming_placeholder.markdown(
                '<div class="typing"><span></span><span></span><span></span></div>',
                unsafe_allow_html=True,
            )

    def stop_generation():
        """Stop: cancel the current stream so the partial gets finalized on
        the next rerun. The next pending turn then naturally takes its place."""
        s = st.session_state.get("stream")
        if s:
            s["cancelled"] = True
            for _ in range(50):  # up to ~1s waiting for the worker to settle
                if s["done"]:
                    break
                time.sleep(0.02)

    st.button("Parar geração", on_click=stop_generation, key="stop")

# Render anything that came AFTER the message currently being answered —
# these are the queued prompts. They render BEFORE the polling loop starts
# so the user sees them parked under the live bubble immediately.
for idx in range(split, len(conv["messages"])):
    _render_message(conv["messages"][idx], queued=idx in queued_idxs)

# Now (everything else painted) kick off / resume the background worker and
# poll it. The thread keeps running across reruns; if the user submits a new
# prompt during this loop, the loop is killed but the worker isn't.
if generating and streaming_idx is not None:
    if _stream is None:
        user_msg = conv["messages"][streaming_idx]
        atts = user_msg.get("attachments", [])
        _stream = _start_stream(
            prompt=user_msg["content"],
            images=[a["data"] for a in atts if _ext(a["name"]) in IMAGE_EXTS] or None,
            audios=[a["data"] for a in atts if _ext(a["name"]) in AUDIO_EXTS] or None,
            target_idx=streaming_idx,
            chat_id=st.session_state.current,
            use_web=user_msg.get("use_web", False),
        )

    while not _stream["done"]:
        text = _stream["text"]
        if text:
            streaming_placeholder.markdown(text)
        time.sleep(0.08)
    streaming_placeholder.markdown(_stream["text"] or "")
    st.rerun()
