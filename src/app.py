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
        background: var(--surface-2);
        border-color: var(--border);
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

    /* Chat input bar: more transparent than the sidebar so the background
       gradient shows through clearly behind the prompt. */
    [data-testid="stChatInput"] {
        background: rgba(0, 0, 0, 0.18);
        border: 1px solid var(--border);
        border-radius: 14px;
        backdrop-filter: blur(4px);
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
    return cid


if "chats" not in st.session_state:
    st.session_state.chats = {}
    st.session_state.next_id = 1
    new_chat()


# --- Sidebar: create / select / delete chats --------------------------------
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
        if delete_col.button("🗑️", key=f"del_{cid}", help="Eliminar conversa"):
            del st.session_state.chats[cid]
            if not st.session_state.chats:
                new_chat()
            elif st.session_state.current == cid:
                st.session_state.current = next(reversed(st.session_state.chats))
            st.rerun()


# --- Main: the active conversation ------------------------------------------
conv = st.session_state.chats[st.session_state.current]
generating = st.session_state.get("generating", False)

# Replay the conversation so far.
for msg in conv["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# New input -> store the user turn and flip into "generating" mode on a rerun,
# so the Stop button can be rendered alongside the streaming answer.
if prompt := st.chat_input("Escreve uma mensagem…"):
    conv["messages"].append({"role": "user", "content": prompt})
    if conv["title"] == "Nova conversa":  # name the chat after its first message
        conv["title"] = prompt[:40] + ("…" if len(prompt) > 40 else "")
    st.session_state.generating = True
    st.rerun()

# Generation phase: stream the answer to the last user turn.
if generating:
    user_prompt = conv["messages"][-1]["content"]

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
        gen = chat.stream_answer(mem, user_prompt)
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
