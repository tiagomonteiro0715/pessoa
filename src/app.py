"""ChatGPT-like Streamlit interface for the Pessoa assistant.

Run with:  uv run streamlit run src/app.py
Assumes Ollama is already running and the models are pulled.
"""
import sys
from pathlib import Path

import streamlit as st

# Make `chat` importable whether run as `streamlit run src/app.py` (script dir
# on sys.path) or from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chat  # noqa: E402

st.set_page_config(page_title="Conversa", layout="centered")

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
        border-radius: 10px;
        border: 1px solid transparent;
        background: transparent;
        color: var(--text);
        text-align: left;
        font-weight: 500;
        transition: background 0.15s ease, border-color 0.15s ease;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255, 255, 255, 0.11);
        border-color: rgba(255, 255, 255, 0.18);
        color: #ffffff;
        box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.04), 0 2px 10px rgba(0, 0, 0, 0.25);
    }
    [data-testid="stSidebar"] .stButton button[kind="primary"] {
        background: var(--surface-2);
        border-color: var(--border);
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

    /* Disclaimer under the chat input */
    .pessoa-disclaimer {
        position: fixed;
        bottom: 0.35rem;
        left: 50%;
        transform: translateX(-50%);
        max-width: 760px;
        width: calc(100% - 2rem);
        text-align: center;
        font-size: 0.7rem;
        line-height: 1.35;
        color: rgba(236, 236, 241, 0.45);
        pointer-events: none;
        z-index: 999;
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
        bottom: 1rem;
        left: 1rem;
        line-height: 1;
        pointer-events: none;
        z-index: 1000;
    }
    .pessoa-brand .name {
        font-size: 1.25rem;
        font-weight: 600;
        color: #ececf1;
        letter-spacing: 0.3px;
    }
    .pessoa-brand .tag {
        font-size: 0.68rem;
        color: rgba(236, 236, 241, 0.45);
        margin-top: 3px;
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
    if st.button("➕ Nova conversa", use_container_width=True):
        new_chat()
        st.rerun()

    st.divider()

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

    st.markdown(
        """
        <div class="pessoa-brand">
            <div class="name">pessoa</div>
            <div class="tag">powered by gemma 4</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --- Main: the active conversation ------------------------------------------
conv = st.session_state.chats[st.session_state.current]
generating = st.session_state.get("generating", False)

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

IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "gif"}
AUDIO_EXTS = {"mp3", "wav", "ogg", "m4a", "flac"}


def _ext(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


# Replay the conversation so far.
for msg in conv["messages"]:
    with st.chat_message(msg["role"]):
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

# Empty-state welcome card: model capabilities, shown only before any turn.
if not conv["messages"] and not generating:
    st.markdown(
        f"""
        <div class="pessoa-welcome">
            <div class="pessoa-welcome-title">Capacidades do modelo</div>
            <div class="pessoa-welcome-row"><b>Modelo</b><span>{chat.MODEL} (multimodal)</span></div>
            <div class="pessoa-welcome-row"><b>Entradas suportadas</b><span>texto, imagem, áudio</span></div>
            <div class="pessoa-welcome-row"><b>Janela de contexto máxima</b><span>128K tokens</span></div>
            <div class="pessoa-welcome-row"><b>Janela em uso (inferência)</b><span>{chat.NUM_CTX:,} tokens — reduzida para resposta mais rápida</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="pessoa-disclaimer">
        pessoa pode cometer erros. Verifica sempre o que ele diz.
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
        })
        if conv["title"] == "Nova conversa":
            seed = text or (attachments[0]["name"] if attachments else "Nova conversa")
            conv["title"] = seed[:40] + ("…" if len(seed) > 40 else "")
            st.session_state.just_named = True
        st.session_state.generating = True
        st.session_state.submit_pulse = True
        st.rerun()

# Generation phase: stream the answer to the last user turn.
# Guard: the user may have switched/deleted chats mid-generation, leaving the
# flag set against a conversation whose last turn isn't theirs (or is empty).
if generating and (not conv["messages"] or conv["messages"][-1]["role"] != "user"):
    st.session_state.generating = False
    generating = False

if generating:
    last_turn = conv["messages"][-1]
    user_prompt = last_turn["content"]
    atts = last_turn.get("attachments", [])
    image_bytes = [a["data"] for a in atts if _ext(a["name"]) in IMAGE_EXTS]
    audio_bytes = [a["data"] for a in atts if _ext(a["name"]) in AUDIO_EXTS]

    def stop_generation():
        """Runs as a button callback at the start of the interrupting rerun:
        save whatever streamed so far and leave generating mode."""
        c = st.session_state.chats[st.session_state.current]
        partial = c.pop("_partial", "")
        if partial:
            c["messages"].append({"role": "assistant", "content": partial + " _(interrompido)_"})
        st.session_state.generating = False

    st.button("Parar geração", on_click=stop_generation, key="stop")

    with st.chat_message("assistant"):
        placeholder = st.empty()
        # Animated dots while we wait for the first token (covers model load on
        # the first run too) — keeps a clean indicator instead of an empty box.
        placeholder.markdown(
            '<div class="typing"><span></span><span></span><span></span></div>',
            unsafe_allow_html=True,
        )
        full = ""
        gen = chat.stream_answer(
            mem,
            user_prompt,
            images=image_bytes or None,
            audios=audio_bytes or None,
        )
        try:
            for piece in gen:
                full += piece
                conv["_partial"] = full          # survive a Stop interruption
                placeholder.markdown(full)        # raises on Stop -> halts cleanly
        except Exception as e:  # Ollama/connection errors (Stop is a BaseException)
            full = full or f"⚠️ Error: {e}"
            placeholder.markdown(full)

    # Reached only on normal completion (Stop unwinds via its callback instead).
    conv["messages"].append({"role": "assistant", "content": full})
    conv.pop("_partial", None)
    st.session_state.generating = False
    st.rerun()  # refresh sidebar title + re-enable the input
