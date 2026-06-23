"""ChatGPT-like Streamlit interface for the Pessoa assistant.

Run with:  uv run streamlit run src/app.py
Assumes Ollama is already running and the models are pulled.
"""
import sys
import time
from pathlib import Path
from threading import Thread

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Make `chat` importable whether run as `streamlit run src/app.py` (script dir
# on sys.path) or from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chat  # noqa: E402

st.set_page_config(page_title="pessoa: runs on gemma 4", layout="centered")

# Dark, professional theme (ChatGPT/Claude-like) over a muted gradient in the
# colors of Portugal: deep green → gold → deep red.
st.markdown(
    """
    <style>
    :root {
        --pt-green: #0a3d22;
        --pt-gold:  #c8a13a;
        --pt-red:   #5a1212;
        --surface:  rgba(255, 255, 255, 0.04);
        --surface-2: rgba(255, 255, 255, 0.07);
        --border:   rgba(255, 255, 255, 0.10);
        --text:     #ececf1;
    }
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(150deg, #03150c 0%, #0a3019 38%, #2c2509 56%, #3a0d0d 78%, #140404 100%);
        background-attachment: fixed;
        color: var(--text);
    }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 820px; padding-top: 3rem; padding-bottom: 7rem; }

    /* Sidebar: black, but transparent so the background gradient shows through */
    [data-testid="stSidebar"] {
        background: rgba(0, 0, 0, 0.45);
        backdrop-filter: blur(6px);
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] .stButton button {
        border-radius: 8px;
        border: none;
        background: transparent;
        color: rgba(236, 236, 241, 0.82);
        text-align: left;
        font-weight: 400;
        font-size: 0.875rem;
        padding: 0.45rem 0.65rem;
        transition: background 0.12s ease, color 0.12s ease;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255, 255, 255, 0.05);
        color: #ffffff;
    }
    [data-testid="stSidebar"] .stButton button[kind="primary"] {
        background: rgba(255, 255, 255, 0.06);
        color: #ffffff;
    }
    /* Delete button: only visible on row hover */
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:last-child .stButton button {
        opacity: 0;
        color: rgba(236, 236, 241, 0.5);
        padding: 0.45rem 0.4rem;
        transition: opacity 0.15s ease, color 0.12s ease;
    }
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:hover > div:last-child .stButton button {
        opacity: 1;
    }
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:last-child .stButton button:hover {
        background: transparent;
        color: #ffffff;
    }
    /* Drop the visible divider — whitespace is enough */
    [data-testid="stSidebar"] hr {
        display: none;
    }

    /* Chat messages -> rounded bubbles */
    [data-testid="stChatMessage"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.6rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
        gap: 0;
    }

    /* Hide the default avatar icons to the left of each message/prompt */
    [data-testid="stChatMessageAvatarUser"],
    [data-testid="stChatMessageAvatarAssistant"],
    [data-testid="stChatMessageAvatar"] {
        display: none;
    }

    /* User prompt bubbles: less transparent than assistant replies, so the
       message you just sent stands out. Matched via the (hidden) user avatar. */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: rgba(16, 24, 18, 0.78);
    }

    /* Chat input bar: transparent body, animated PT-flag gradient as the
       border (drawn via a masked ::before so we don't touch the textarea). */
    [data-testid="stChatInput"] {
        position: relative;
        background: rgba(0, 0, 0, 0.18);
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        border-radius: 14px;
        backdrop-filter: blur(4px);
    }
    [data-testid="stChatInput"]::before {
        content: '';
        position: absolute;
        inset: 0;
        padding: 1.6px;
        border-radius: 14px;
        background: linear-gradient(
            90deg,
            #5a1212, #c8a13a, #0a3d22, #c8a13a, #5a1212
        );
        background-size: 300% 100%;
        -webkit-mask:
            linear-gradient(#000 0 0) content-box,
            linear-gradient(#000 0 0);
        -webkit-mask-composite: xor;
                mask-composite: exclude;
        animation: pessoa-border-flow 30s linear infinite;
        pointer-events: none;
        z-index: 1;
        filter: brightness(1) saturate(1);
        transition: filter 0.6s ease-out;
    }
    /* Burst on submit: animation runs ~22x faster and glows. Class is added
       by JS on submit and removed after the burst window. */
    body.pessoa-pulse [data-testid="stChatInput"]::before {
        animation-duration: 1.5s;
        filter: brightness(1.55) saturate(1.3) drop-shadow(0 0 7px rgba(200, 161, 58, 0.6));
        transition: filter 0.12s ease-in;
    }
    @keyframes pessoa-border-flow {
        from { background-position:   0% 50%; }
        to   { background-position: 300% 50%; }
    }
    [data-testid="stChatInput"] textarea {
        color: var(--text);
        background: transparent;
    }
    /* Streamlit wraps the input bottom area in its own container — clear it too
       so no opaque band sits behind the transparent prompt. */
    [data-testid="stBottomBlockContainer"],
    [data-testid="stBottom"] > div {
        background: transparent;
    }

    /* Typing indicator shown while waiting for the first token (no empty box) */
    .typing { display: inline-flex; gap: 6px; padding: 2px; }
    .typing span {
        width: 7px; height: 7px; border-radius: 50%;
        background: var(--pt-gold);
        animation: typing-bounce 1.2s infinite ease-in-out;
    }
    .typing span:nth-child(2) { animation-delay: 0.18s; }
    .typing span:nth-child(3) { animation-delay: 0.36s; }
    @keyframes typing-bounce {
        0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
        30%           { opacity: 1;   transform: translateY(-4px); }
    }

    /* Subtle gold accent on focus / scrollbar */
    ::-webkit-scrollbar { width: 9px; }
    ::-webkit-scrollbar-thumb {
        background: rgba(200, 161, 58, 0.3);
        border-radius: 6px;
    }

    /* Welcome / capabilities card shown before the first turn */
    .pessoa-welcome {
        max-width: 560px;
        margin: 2rem auto 1.5rem auto;
        padding: 1.25rem 1.5rem;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        backdrop-filter: blur(6px);
        color: var(--text);
        animation: pessoa-welcome-in 0.45s ease-out;
    }
    .pessoa-welcome-title {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: rgba(236, 236, 241, 0.5);
        margin-bottom: 0.9rem;
    }
    .pessoa-welcome-row {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 1rem;
        font-size: 0.88rem;
        padding: 0.35rem 0;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
    .pessoa-welcome-row:first-of-type { border-top: none; }
    .pessoa-welcome-row b {
        font-weight: 500;
        color: rgba(236, 236, 241, 0.7);
    }
    .pessoa-welcome-row span {
        text-align: right;
        color: var(--text);
    }
    @keyframes pessoa-welcome-in {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* Queued prompts: bubbles containing the .pessoa-queued-tag get a muted
       look — lower opacity, dashed border, pulsing dot — to show they're
       waiting for the active stream to finish. */
    [data-testid="stChatMessage"]:has(.pessoa-queued-tag) {
        opacity: 0.55;
        background: rgba(16, 24, 18, 0.35) !important;
        border: 1px dashed rgba(200, 161, 58, 0.45) !important;
        box-shadow: none !important;
    }
    .pessoa-queued-tag {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        font-size: 0.72rem;
        font-style: italic;
        color: rgba(236, 236, 241, 0.7);
        margin-bottom: 0.5rem;
    }
    .pessoa-queued-tag::before {
        content: '';
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--pt-gold);
        animation: pessoa-queued-pulse 1.4s ease-in-out infinite;
    }
    @keyframes pessoa-queued-pulse {
        0%, 100% { opacity: 0.3; transform: scale(0.85); }
        50%      { opacity: 1;   transform: scale(1.1); }
    }

    /* Disclaimer: rendered as a pseudo-element of the bottom container so it
       sits directly below the chat input — not pinned to viewport bottom. */
    [data-testid="stBottomBlockContainer"]::after {
        content: 'pessoa pode cometer erros. Verifica sempre o que ele diz.';
        display: block;
        text-align: center;
        font-size: 0.7rem;
        line-height: 1.35;
        color: rgba(236, 236, 241, 0.45);
        padding: 0.45rem 1rem 0.1rem 1rem;
        pointer-events: none;
    }

    /* Hide Streamlit's "Ask Google / Ask ChatGPT" links on exception cards */
    [data-testid="stException"] a[href*="google.com"],
    [data-testid="stException"] a[href*="chatgpt.com"],
    [data-testid="stException"] a[href*="chat.openai"],
    .stException a[href*="google.com"],
    .stException a[href*="chatgpt.com"],
    .stException a[href*="chat.openai"] {
        display: none !important;
    }

    /* Pull the sidebar content closer to the top */
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        padding-top: 1.2rem;
        padding-bottom: 5rem;  /* leave room for the pinned footer */
    }

    /* "pessoa" wordmark pinned to the bottom-left of the sidebar */
    .pessoa-brand {
        position: fixed;
        bottom: 0.9rem;
        left: 1rem;
        line-height: 1.2;
        pointer-events: none;
        z-index: 1000;
    }
    .pessoa-brand .name {
        font-size: 0.92rem;
        font-weight: 500;
        color: rgba(236, 236, 241, 0.78);
        letter-spacing: 0.2px;
    }
    .pessoa-brand .tag {
        font-size: 0.66rem;
        color: rgba(236, 236, 241, 0.35);
        margin-top: 2px;
    }
    .pessoa-brand .repo {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        margin-top: 6px;
        font-size: 0.66rem;
        color: rgba(236, 236, 241, 0.4);
        text-decoration: none;
        pointer-events: auto;
        transition: color 0.12s ease;
    }
    .pessoa-brand .repo:hover {
        color: rgba(236, 236, 241, 0.85);
    }
    .pessoa-brand .repo svg {
        opacity: 0.7;
    }

    /* New chat / renamed chat animations -------------------------------- */
    @keyframes chat-slide-in {
        from { opacity: 0; transform: translateY(-6px); max-height: 0; }
        to   { opacity: 1; transform: translateY(0);    max-height: 60px; }
    }
    @keyframes chat-typewriter {
        from { clip-path: inset(0 100% 0 0); }
        to   { clip-path: inset(0 0     0 0); }
    }
    .pessoa-just-created [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:first-of-type {
        animation: chat-slide-in 0.32s ease-out;
    }
    .pessoa-just-named [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:first-of-type .stButton button p {
        animation: chat-typewriter 0.55s steps(28, end);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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
# chats: {chat_id: {"title": str, "messages": [{"role", "content"}, ...]}}
def new_chat() -> int:
    cid = st.session_state.next_id
    st.session_state.next_id += 1
    st.session_state.chats[cid] = {"title": "Nova conversa", "messages": []}
    st.session_state.current = cid
    st.session_state.just_created = True
    return cid


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

with st.sidebar:
    if st.button("Nova conversa", use_container_width=True, key="new_chat_btn"):
        new_chat()
        st.rerun()
    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    for cid, conv in reversed(list(st.session_state.chats.items())):
        select_col, delete_col = st.columns([5, 1])
        label = conv["title"] or "Nova conversa"
        is_current = cid == st.session_state.current
        if select_col.button(
            label,
            key=f"sel_{cid}",
            use_container_width=True,
            type="primary" if is_current else "secondary",
        ):
            st.session_state.current = cid
            st.rerun()
        if delete_col.button("×", key=f"del_{cid}", help="Eliminar conversa"):
            del st.session_state.chats[cid]
            if not st.session_state.chats:
                new_chat()
            elif st.session_state.current == cid:
                st.session_state.current = next(reversed(st.session_state.chats))
            st.rerun()

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    st.toggle("🌐 Internet", key="use_web", help="Anexa resultados do DuckDuckGo ao prompt.")

    st.markdown(
        """
        <div class="pessoa-brand">
            <div class="name">pessoa</div>
            <div class="tag">runs on gemma 4</div>
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
