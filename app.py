"""RepoGuide AI - understand any codebase, one step at a time.

Local-first: every prompt goes to an open-weight model running in Ollama on
your own machine. No API keys, no data leaving the computer.
"""

from __future__ import annotations

import time

import streamlit as st

from repoguide import config
from repoguide.ingest import (
    Ingest,
    from_github,
    from_text,
    from_uploads,
    max_chars_for,
    render,
)
from repoguide.ollama import ModelMissing, OllamaClient, OllamaError
from repoguide.prompts import MODES, build_analysis_messages

# --------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------
st.set_page_config(
    page_title=f"{config.APP_NAME} · {config.VERSION}",
    page_icon=config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
  .stApp { background-color: #0a0c10; }

  .block-container {
    max-width: 1080px !important;
    padding-top: 2.5rem !important;
    padding-bottom: 4rem !important;
  }

  /* ---------- header ---------- */
  .rg-header { text-align: center; margin-bottom: 2rem; }
  .rg-title {
    font-size: 2.9rem; font-weight: 800; margin: 0 0 .35rem 0;
    background: linear-gradient(90deg, #58a6ff, #bc8cff);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; line-height: 1.15;
  }
  .rg-tagline { color: #8b949e; font-size: 1.05rem; margin: 0 0 .9rem 0; }
  .rg-badges { display: flex; gap: .5rem; justify-content: center; flex-wrap: wrap; }
  .rg-badge {
    padding: 4px 12px; border-radius: 999px; background: #161b22;
    border: 1px solid #30363d; color: #58a6ff; font-size: .72rem;
    font-weight: 600; letter-spacing: .06em; text-transform: uppercase;
  }
  .rg-badge.green { color: #3fb950; }
  .rg-badge.dim { color: #8b949e; }

  /* ---------- cards ---------- */
  .st-key-input_card, .st-key-result_card {
    background: #0d1117;
    border: 1px solid #30363d !important;
    border-radius: 16px !important;
    padding: 1.5rem 1.6rem !important;
    box-shadow: 0 8px 28px rgba(0,0,0,.35);
  }
  .st-key-result_card { border-left: 3px solid #58a6ff !important; }

  .rg-section {
    color: #c9d1d9; font-size: .95rem; font-weight: 600;
    letter-spacing: .04em; text-transform: uppercase; margin: 0 0 .9rem 0;
  }

  /* ---------- widgets ---------- */
  .stTextArea textarea, .stTextInput input {
    background: #010409 !important; color: #c9d1d9 !important;
    border: 1px solid #30363d !important; border-radius: 8px !important;
    font-family: 'JetBrains Mono', 'Consolas', monospace !important;
    font-size: .88rem !important;
  }
  .stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #58a6ff !important;
    box-shadow: 0 0 0 1px #58a6ff !important;
  }

  div.stButton > button {
    border-radius: 8px !important; font-weight: 600 !important;
    border: 1px solid #30363d !important; transition: all .15s ease;
  }
  div.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #1f6feb, #8957e5) !important;
    border: none !important; color: #fff !important;
  }
  div.stButton > button[kind="primary"]:hover { filter: brightness(1.15); }
  div.stButton > button[kind="secondary"] {
    background: #21262d !important; color: #c9d1d9 !important;
  }
  div.stButton > button[kind="secondary"]:hover {
    border-color: #58a6ff !important; color: #58a6ff !important;
  }

  /* ---------- tabs ---------- */
  .stTabs [data-baseweb="tab-list"] { gap: .35rem; }
  .stTabs [data-baseweb="tab"] {
    background: #161b22; border-radius: 8px 8px 0 0;
    padding: .5rem 1rem; color: #8b949e;
  }
  .stTabs [aria-selected="true"] { background: #1f6feb22; color: #f0f6fc; }

  /* ---------- markdown output ---------- */
  [data-testid="stMarkdownContainer"] code {
    background: #161b22; color: #ff7b72; padding: 2px 6px;
    border-radius: 4px; border: 1px solid #30363d; font-size: .86em;
  }
  [data-testid="stMarkdownContainer"] pre {
    background: #010409 !important; border: 1px solid #30363d;
    border-radius: 8px; padding: .9rem;
  }
  [data-testid="stMarkdownContainer"] h2 {
    color: #f0f6fc; font-size: 1.25rem; margin-top: 1.6rem;
    padding-bottom: .35rem; border-bottom: 1px solid #21262d;
  }
  [data-testid="stMarkdownContainer"] h3 { color: #f0f6fc; font-size: 1.05rem; }
  [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {
    color: #c9d1d9; line-height: 1.7;
  }

  /* ---------- misc ---------- */
  .rg-footer {
    text-align: center; color: #484f58; font-size: .78rem; padding: 2.5rem 0 0 0;
  }
  .rg-hint { color: #8b949e; font-size: .82rem; }
  [data-testid="stSidebar"] { background: #0d1117; }
</style>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------
DEFAULTS = {
    "model_messages": None,   # what we send to the model
    "transcript": [],         # what we show the user
    "context_stats": None,
    "pending_analysis": False,
    "analysis_meta": None,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_analysis() -> None:
    st.session_state.model_messages = None
    st.session_state.transcript = []
    st.session_state.context_stats = None
    st.session_state.analysis_meta = None
    st.session_state.pending_analysis = False


client = OllamaClient()

# --------------------------------------------------------------------------
# Sidebar: connection + model + settings
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### {config.APP_ICON} {config.APP_NAME}")
    st.caption(f"v{config.VERSION} · local & private")

    is_up, health_message = client.health()
    if is_up:
        st.success(health_message, icon="✅")
        models = []
        try:
            models = client.list_models()
        except OllamaError as exc:
            st.error(str(exc))
    else:
        st.error(health_message, icon="⚠️")
        models = []

    if models:
        labels = {m.name: m.label for m in models}
        selected_model = st.selectbox(
            "Model",
            options=[m.name for m in models],
            format_func=lambda name: labels.get(name, name),
            help="Every model listed here runs locally via Ollama.",
        )
    else:
        selected_model = None
        st.info(
            "No models installed yet.\n\n"
            "```\nollama pull gemma\n```",
            icon="📥",
        )

    with st.expander("Advanced", expanded=False):
        temperature = st.slider(
            "Temperature", 0.0, 1.0, 0.3, 0.05,
            help="Lower = more literal and predictable. Higher = more creative.",
        )
        num_ctx = st.select_slider(
            "Context window (tokens)",
            options=config.NUM_CTX_CHOICES,
            value=config.DEFAULT_NUM_CTX,
            help="Larger lets you analyse bigger files, but needs more RAM.",
        )
        budget_chars = max_chars_for(num_ctx)
        st.caption(
            f"≈ {budget_chars:,} characters of source "
            f"(≈ {budget_chars // 1024} KB) per analysis."
        )

    if st.button("↺ Reset session", use_container_width=True):
        reset_analysis()
        st.rerun()

    with st.expander("Recommended open-weight models"):
        for rec in config.RECOMMENDED_MODELS:
            installed = any(m.name.startswith(rec["tag"].split(":")[0]) for m in models)
            mark = "✅ installed" if installed else "⬇️ not installed"
            st.markdown(f"**{rec['label']}** · {mark}")
            st.caption(rec["why"])
            if not installed:
                st.code(f"ollama pull {rec['tag']}", language="bash")

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
model_badge = selected_model or "no model"
st.markdown(
    f"""
<div class="rg-header">
  <h1 class="rg-title">{config.APP_ICON} {config.APP_NAME}</h1>
  <p class="rg-tagline">Understand any codebase, one step at a time.</p>
  <div class="rg-badges">
    <span class="rg-badge">{model_badge}</span>
    <span class="rg-badge green">100% local</span>
    <span class="rg-badge dim">open weights</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Input card
# --------------------------------------------------------------------------
with st.container(border=True, key="input_card"):
    st.markdown('<p class="rg-section">1 · Where is the code?</p>', unsafe_allow_html=True)

    tab_paste, tab_upload, tab_github = st.tabs(["📋 Paste", "📁 Upload", "🔗 GitHub"])

    with tab_paste:
        pasted = st.text_area(
            "Paste code or a README",
            height=220,
            placeholder="Paste a snippet, a file, or a whole README.md …",
            label_visibility="collapsed",
        )

    with tab_upload:
        uploads = st.file_uploader(
            "Drop source files or a .zip of the project",
            accept_multiple_files=True,
            help=f"Up to {config.MAX_FILES} files. Individual files under "
                 f"{config.MAX_FILE_BYTES // 1000} KB.",
            label_visibility="collapsed",
        )
        st.caption(
            "Source files (`.py`, `.js`, `.java`, …) and `.zip` archives. "
            "Binary files and build folders are skipped automatically."
        )

    with tab_github:
        github_url = st.text_input(
            "Public GitHub repository URL",
            placeholder="https://github.com/owner/repo",
            label_visibility="collapsed",
        )
        st.caption(
            "Public repos only. The archive is downloaded once, filtered to source "
            "files, and never stored on disk."
        )

    st.markdown(
        '<p class="rg-section" style="margin-top:1.4rem">2 · What should I do with it?</p>',
        unsafe_allow_html=True,
    )
    mode_id = st.radio(
        "Analysis type",
        options=list(MODES.keys()),
        format_func=lambda key: f"{MODES[key]['icon']}  {MODES[key]['label']}",
        horizontal=True,
        label_visibility="collapsed",
    )
    st.markdown(
        f'<p class="rg-hint">{MODES[mode_id]["help"]}</p>', unsafe_allow_html=True
    )

    analyze = st.button(
        "✨ Analyze",
        type="primary",
        use_container_width=True,
        disabled=selected_model is None,
    )


# --------------------------------------------------------------------------
# Gather input and kick off the analysis
# --------------------------------------------------------------------------
def collect_ingest() -> Ingest | None:
    """Pick whichever input tab actually holds something."""
    if pasted and pasted.strip():
        return from_text(pasted)
    if uploads:
        return from_uploads(uploads)
    if github_url and github_url.strip():
        with st.spinner("Downloading repository…"):
            ingest = from_github(github_url)
        if not ingest and ingest.skipped:
            st.error(f"Couldn't use that repository: {ingest.skipped[0]}")
            return None
        return ingest
    return None


if analyze:
    reset_analysis()
    ingest = collect_ingest()

    if ingest is None:
        st.warning("Add something to analyse first — paste, upload, or paste a GitHub URL.")
    elif not ingest:
        st.error("No readable source files found in that input.")
    else:
        context = render(ingest, budget_chars)
        if not context.text.strip():
            st.error("Nothing fit inside the context window. Try a bigger context size.")
        else:
            st.session_state.context_stats = context
            st.session_state.model_messages = build_analysis_messages(
                mode_id,
                context.text,
                included=context.included,
                dropped=context.dropped,
                truncated=context.truncated,
            )
            st.session_state.analysis_meta = {
                "mode": f"{MODES[mode_id]['icon']} {MODES[mode_id]['label']}",
                "source": ingest.source,
                "files": context.included,
                "skipped": len(ingest.skipped),
            }
            st.session_state.pending_analysis = True
            st.rerun()


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------
def stream_reply(messages: list[dict]):
    """Generator handed to st.write_stream."""
    return client.chat_stream(
        selected_model,
        messages,
        temperature=temperature,
        num_ctx=num_ctx,
    )


stats = st.session_state.context_stats
if stats is not None:
    meta = st.session_state.analysis_meta or {}
    st.markdown(
        f"""
<div class="rg-badges" style="justify-content:flex-start;margin:1.6rem 0 .6rem 0">
  <span class="rg-badge">{meta.get('mode', 'analysis')}</span>
  <span class="rg-badge dim">{meta.get('files', 0)} files · ≈{stats.approx_tokens:,} tok</span>
  <span class="rg-badge dim">{meta.get('source', '')}</span>
</div>
""",
        unsafe_allow_html=True,
    )

    if stats.dropped or stats.truncated:
        bits = []
        if stats.dropped:
            bits.append(f"{stats.dropped} file(s) didn't fit")
        if stats.truncated:
            bits.append("one file was truncated")
        st.caption(
            "⚠️ " + " and ".join(bits) + ". Raise the context window in Advanced, "
            "or analyse fewer files at once."
        )

    with st.container(border=True, key="result_card"):
        # 1. Everything said so far.
        for message in st.session_state.transcript:
            avatar = "📚" if message["role"] == "assistant" else "🧑‍💻"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])

        # 2. The answer we still owe the user, streamed live.
        if st.session_state.pending_analysis:
            st.session_state.pending_analysis = False
            with st.chat_message("assistant", avatar="📚"):
                started = time.perf_counter()
                try:
                    answer = st.write_stream(
                        stream_reply(st.session_state.model_messages)
                    )
                except (ModelMissing, OllamaError) as exc:
                    st.error(str(exc))
                    answer = None

                if answer:
                    elapsed = time.perf_counter() - started
                    st.session_state.model_messages.append(
                        {"role": "assistant", "content": answer}
                    )
                    st.session_state.transcript.append(
                        {"role": "assistant", "content": answer}
                    )
                    st.caption(f"⏱ {elapsed:.1f}s")

    # -- follow-up questions ------------------------------------------------
    question = st.chat_input("Ask a follow-up about this code…")
    if question:
        st.session_state.model_messages.append({"role": "user", "content": question})
        st.session_state.transcript.append({"role": "user", "content": question})

        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(question)

        with st.chat_message("assistant", avatar="📚"):
            started = time.perf_counter()
            try:
                answer = st.write_stream(stream_reply(st.session_state.model_messages))
            except OllamaError as exc:
                st.error(str(exc))
                answer = None
            if answer:
                st.session_state.model_messages.append({"role": "assistant", "content": answer})
                st.session_state.transcript.append({"role": "assistant", "content": answer})
                st.caption(f"⏱ {time.perf_counter() - started:.1f}s")

    # -- export -------------------------------------------------------------
    if st.session_state.transcript:
        export = [
            f"# {config.APP_NAME} — {meta.get('mode', 'Analysis')}",
            f"\n_Source: {meta.get('source', '')} · {meta.get('files', 0)} files · "
            f"model `{selected_model}`_\n",
        ]
        for message in st.session_state.transcript:
            role = "### 🧑‍💻 You" if message["role"] == "user" else "### 📚 RepoGuide"
            export.append(f"\n{role}\n\n{message['content']}\n")
        st.download_button(
            "⬇️  Download this analysis (.md)",
            data="".join(export),
            file_name="repoguide-analysis.md",
            mime="text/markdown",
        )

if stats is None and not analyze:
    with st.container(border=True):
        st.markdown(
            """
<p class="rg-hint">
Nothing analysed yet. Pick an input above and hit <b>Analyze</b> — everything
runs on your machine, so nothing you paste leaves your computer.
</p>
""",
            unsafe_allow_html=True,
        )

st.markdown(
    f'<div class="rg-footer">{config.APP_NAME} v{config.VERSION} · runs on '
    f'Ollama · your code never leaves this machine</div>',
    unsafe_allow_html=True,
)
