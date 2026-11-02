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
    initial_sidebar_state="auto",
)

st.markdown(
    """
<style>
  /* ============================================================
     RepoGuide AI — modern dark theme
     Pure CSS. No behaviour changes.
     ============================================================ */

  :root {
    --rg-bg: #07080d;
    --rg-border: rgba(255, 255, 255, 0.075);
    --rg-border-hi: rgba(255, 255, 255, 0.16);
    --rg-text: #e6edf3;
    --rg-muted: #98a2b3;
    --rg-violet: #8b5cf6;
    --rg-cyan: #22d3ee;
    --rg-grad: linear-gradient(135deg, #8b5cf6 0%, #6366f1 45%, #22d3ee 100%);
    --rg-ease: cubic-bezier(.22, .61, .36, 1);
  }

  html, body, .stApp {
    font-family: ui-sans-serif, -apple-system, "Segoe UI Variable Text",
                 "Segoe UI", Inter, system-ui, sans-serif;
  }

  /* ---------- backdrop ---------- */
  .stApp {
    background-color: var(--rg-bg);
    background-image:
      radial-gradient(900px 480px at 12% -8%, rgba(139, 92, 246, .20), transparent 62%),
      radial-gradient(760px 420px at 92% 2%, rgba(34, 211, 238, .14), transparent 58%),
      radial-gradient(900px 600px at 50% 112%, rgba(99, 102, 241, .12), transparent 62%),
      linear-gradient(rgba(255, 255, 255, .018) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255, 255, 255, .018) 1px, transparent 1px);
    background-size: auto, auto, auto, 48px 48px, 48px 48px;
    background-attachment: fixed;
    color: var(--rg-text);
  }

  [data-testid="stHeader"] { background: transparent; }
  [data-testid="stAppDeployButton"] { display: none; }

  .block-container {
    max-width: 1120px !important;
    padding-top: 2rem !important;
    padding-bottom: 5rem !important;
  }

  /* ---------- header ---------- */
  .rg-header {
    position: relative;
    text-align: center;
    padding: 2.6rem 1rem 1.5rem;
    margin-bottom: 1rem;
    overflow: hidden;
    border-radius: 28px;
  }

  .rg-title {
    position: relative;
    font-size: clamp(2.2rem, 4.6vw, 3.5rem);
    font-weight: 800;
    letter-spacing: -.03em;
    margin: 0 0 .5rem;
    background: linear-gradient(100deg, #c4b5fd, #8b5cf6 28%, #22d3ee 58%, #c4b5fd 88%);
    background-size: 240% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: rg-shimmer 10s ease-in-out infinite;
  }

  @keyframes rg-shimmer {
    0%, 100% { background-position: 0% 50%; }
    50%      { background-position: 100% 50%; }
  }

  .rg-tagline {
    position: relative;
    color: var(--rg-muted);
    font-size: 1.02rem;
    margin: 0 0 1.15rem;
  }

  .rg-badges {
    display: flex;
    gap: .5rem;
    justify-content: center;
    flex-wrap: wrap;
    position: relative;
  }

  .rg-badge {
    display: inline-flex;
    align-items: center;
    gap: .45rem;
    padding: .38rem .8rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, .035);
    border: 1px solid var(--rg-border);
    color: #cbd5e1;
    font-size: .72rem;
    font-weight: 600;
    letter-spacing: .07em;
    text-transform: uppercase;
    backdrop-filter: blur(10px);
    transition: border-color .2s var(--rg-ease), color .2s, transform .2s;
  }
  .rg-badge:hover {
    border-color: rgba(139, 92, 246, .45);
    transform: translateY(-1px);
  }
  .rg-badge::before {
    content: "";
    width: 6px; height: 6px;
    border-radius: 50%;
    background: currentColor;
    opacity: .85;
  }
  .rg-badge.green { color: #4ade80; }
  .rg-badge.green::before { animation: rg-pulse 2s ease-in-out infinite; }
  .rg-badge.dim { color: var(--rg-muted); }

  @keyframes rg-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(74, 222, 128, .5); }
    50%      { box-shadow: 0 0 0 5px rgba(74, 222, 128, 0); }
  }

  /* ---------- glass cards ---------- */
  .st-key-input_card,
  .st-key-result_card {
    position: relative;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, .045), rgba(255, 255, 255, .012)),
      rgba(15, 17, 24, .78);
    border: 1px solid var(--rg-border) !important;
    border-radius: 22px !important;
    padding: 1.5rem 1.6rem 1.3rem !important;
    backdrop-filter: blur(20px) saturate(140%);
    box-shadow: 0 24px 60px -28px rgba(0, 0, 0, .9), inset 0 1px 0 rgba(255, 255, 255, .06);
    transition: border-color .3s var(--rg-ease), box-shadow .3s var(--rg-ease), transform .3s var(--rg-ease);
  }
  .st-key-input_card:hover {
    border-color: rgba(139, 92, 246, .30) !important;
    box-shadow: 0 30px 70px -28px rgba(0, 0, 0, .95),
                0 0 0 1px rgba(139, 92, 246, .10),
                inset 0 1px 0 rgba(255, 255, 255, .08);
  }
  .st-key-result_card:hover {
    border-color: rgba(139, 92, 246, .35) !important;
    box-shadow: 0 30px 70px -28px rgba(0, 0, 0, .95),
                0 0 0 1px rgba(139, 92, 246, .12),
                inset 0 1px 0 rgba(255, 255, 255, .08);
    transform: translateY(-2px);
  }

  .st-key-result_card::before {
    content: "";
    position: absolute;
    left: 0; top: 26px; bottom: 26px;
    width: 2px;
    border-radius: 2px;
    background: var(--rg-violet);
    box-shadow: 0 0 18px rgba(139, 92, 246, .55);
  }

  /* ---------- section labels ---------- */
  .rg-section {
    display: flex;
    align-items: center;
    gap: .6rem;
    color: #cbd5e1;
    font-size: .8rem;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    margin: 0 0 1rem;
  }
  .rg-section::before {
    content: "";
    width: 22px; height: 2px;
    border-radius: 2px;
    background: var(--rg-violet);
  }

  /* ---------- tabs ---------- */
  [data-testid="stTabs"] [role="tablist"] {
    gap: .3rem;
    padding: .3rem;
    border-radius: 14px;
    background: rgba(255, 255, 255, .03);
    border: 1px solid var(--rg-border);
    width: fit-content;
  }
  [data-testid="stTabs"] [data-testid="stTab"] {
    border-radius: 10px;
    padding: .42rem .95rem;
    color: var(--rg-muted);
    cursor: pointer;
    user-select: none;
    transition: color .22s var(--rg-ease), background .22s var(--rg-ease), box-shadow .22s var(--rg-ease);
  }
  [data-testid="stTabs"] [data-testid="stTab"] p {
    margin: 0 !important;
    font-size: .92rem;
    font-weight: 600;
  }
  [data-testid="stTabs"] [data-testid="stTab"]:hover {
    color: #e2e8f0;
    background: rgba(255, 255, 255, .05);
  }
  [data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {
    color: #fff;
    background: rgba(139, 92, 246, .16);
    box-shadow: inset 0 0 0 1px rgba(139, 92, 246, .32);
  }
  [data-testid="stTabs"] .react-aria-SelectionIndicator { display: none; }

  /* ---------- mode pills (radio) ---------- */
  [data-testid="stRadioGroup"] {
    gap: .5rem;
    flex-wrap: wrap;
  }
  [data-testid="stRadioOption"] {
    padding: .55rem .95rem;
    border-radius: 12px;
    background: rgba(255, 255, 255, .03);
    border: 1px solid var(--rg-border);
    cursor: pointer;
    transition: all .22s var(--rg-ease);
  }
  [data-testid="stRadioOption"]:hover {
    border-color: rgba(139, 92, 246, .5);
    background: rgba(139, 92, 246, .08);
    transform: translateY(-1px);
  }
  [data-testid="stRadioOption"][data-selected="true"] {
    border-color: rgba(139, 92, 246, .55);
    background: rgba(139, 92, 246, .16);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, .08);
  }
  [data-testid="stRadioOption"] p {
    margin: 0 !important;
    font-size: .93rem;
    font-weight: 600;
    color: #e2e8f0;
  }
  /* hide the native radio dot */
  [data-testid="stRadioOption"] > div > div:first-child { display: none; }

  /* ---------- inputs ---------- */
  .stTextArea textarea,
  .stTextInput input,
  [data-testid="stSelectbox"] input {
    background: rgba(5, 6, 10, .75) !important;
    color: var(--rg-text) !important;
    border: 1px solid var(--rg-border) !important;
    border-radius: 12px !important;
    font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace !important;
    font-size: .92rem !important;
    transition: border-color .2s, box-shadow .2s, background .2s;
  }
  .stTextArea textarea:focus,
  .stTextInput input:focus,
  [data-testid="stSelectbox"] input:focus {
    border-color: rgba(139, 92, 246, .7) !important;
    box-shadow: 0 0 0 3px rgba(139, 92, 246, .18) !important;
    background: rgba(5, 6, 10, .95) !important;
  }
  .stTextArea textarea::placeholder,
  .stTextInput input::placeholder { color: #5b6472 !important; }

  /* ---------- buttons ---------- */
  .stButton > button,
  .stDownloadButton > button {
    border-radius: 12px !important;
    font-weight: 650 !important;
    border: 1px solid var(--rg-border) !important;
    position: relative;
    overflow: hidden;
    transition: transform .18s var(--rg-ease), box-shadow .22s,
                filter .22s, border-color .22s, background .22s, color .22s;
  }
  .stButton > button:active,
  .stDownloadButton > button:active { transform: scale(.985); }

  .stButton > button[kind="primary"] {
    background: var(--rg-grad) !important;
    color: #fff !important;
    border: none !important;
    box-shadow: 0 12px 30px -12px rgba(99, 102, 241, .85),
                inset 0 1px 0 rgba(255, 255, 255, .25);
  }
  .stButton > button[kind="primary"]:hover {
    filter: brightness(1.08) saturate(1.1);
    transform: translateY(-1px);
    box-shadow: 0 16px 40px -12px rgba(99, 102, 241, 1),
                inset 0 1px 0 rgba(255, 255, 255, .3);
  }
  .stButton > button[kind="primary"]::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(110deg, transparent 20%, rgba(255, 255, 255, .28) 45%, transparent 70%);
    transform: translateX(-120%);
    transition: transform .7s var(--rg-ease);
  }
  .stButton > button[kind="primary"]:hover::after { transform: translateX(120%); }

  .stButton > button[kind="secondary"] {
    background: rgba(255, 255, 255, .045) !important;
    color: #d7dee8 !important;
  }
  .stButton > button[kind="secondary"]:hover {
    background: rgba(255, 255, 255, .08) !important;
    border-color: rgba(139, 92, 246, .45) !important;
    color: #fff !important;
    transform: translateY(-1px);
  }

  /* ---------- file uploader ---------- */
  [data-testid="stFileUploaderDropzone"] {
    background: rgba(255, 255, 255, .02);
    border: 1.5px dashed rgba(255, 255, 255, .14);
    border-radius: 16px;
    transition: border-color .25s var(--rg-ease), background .25s var(--rg-ease);
  }
  [data-testid="stFileUploaderDropzone"]:hover {
    border-color: rgba(139, 92, 246, .6);
    background: rgba(139, 92, 246, .06);
  }

  /* ---------- chat ---------- */
  [data-testid="stChatMessage"] {
    background: rgba(255, 255, 255, .03);
    border: 1px solid var(--rg-border);
    border-radius: 16px;
    padding: .35rem .25rem;
    animation: rg-rise .35s var(--rg-ease);
  }
  @keyframes rg-rise {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: none; }
  }
  [data-testid="stChatInput"] {
    background: rgba(15, 17, 24, .9);
    border: 1px solid var(--rg-border);
    border-radius: 14px;
    transition: border-color .2s;
  }
  [data-testid="stChatInput"]:focus-within {
    border-color: rgba(139, 92, 246, .55);
  }

  /* ---------- sidebar ---------- */
  [data-testid="stSidebar"] {
    background: rgba(10, 11, 17, .94);
    border-right: 1px solid var(--rg-border);
    backdrop-filter: blur(20px);
  }
  [data-testid="stSidebar"] .block-container {
    padding-top: 1.6rem !important;
  }

  /* ---------- expander ---------- */
  [data-testid="stExpander"] details {
    border: 1px solid var(--rg-border);
    border-radius: 14px;
    background: rgba(255, 255, 255, .02);
    overflow: hidden;
    transition: border-color .2s var(--rg-ease);
  }
  [data-testid="stExpander"] details:hover { border-color: rgba(255, 255, 255, .16); }
  [data-testid="stExpander"] summary { border-radius: 14px; }

  /* ---------- markdown output ---------- */
  [data-testid="stMarkdownContainer"] h1,
  [data-testid="stMarkdownContainer"] h2,
  [data-testid="stMarkdownContainer"] h3 {
    color: #f1f5f9;
    letter-spacing: -.01em;
  }
  [data-testid="stMarkdownContainer"] h2 {
    font-size: 1.18rem;
    margin-top: 1.7rem;
    padding-bottom: .45rem;
    border-bottom: 1px solid rgba(255, 255, 255, .07);
  }
  [data-testid="stMarkdownContainer"] h3 { font-size: 1.02rem; }
  [data-testid="stMarkdownContainer"] p,
  [data-testid="stMarkdownContainer"] li {
    color: #cbd5e1;
    line-height: 1.72;
  }
  [data-testid="stMarkdownContainer"] code {
    background: rgba(139, 92, 246, .12);
    color: #c4b5fd;
    padding: 2px 6px;
    border-radius: 6px;
    border: 1px solid rgba(139, 92, 246, .22);
    font-size: .86em;
  }
  [data-testid="stMarkdownContainer"] pre {
    background: rgba(2, 3, 7, .9) !important;
    border: 1px solid var(--rg-border);
    border-radius: 12px;
    padding: 1rem;
  }
  [data-testid="stMarkdownContainer"] pre code {
    background: none;
    border: none;
    padding: 0;
    color: #e2e8f0;
  }
  [data-testid="stMarkdownContainer"] a {
    color: #a78bfa;
    text-decoration: none;
    border-bottom: 1px solid rgba(167, 139, 250, .35);
  }
  [data-testid="stMarkdownContainer"] a:hover {
    color: #c4b5fd;
    border-bottom-color: #c4b5fd;
  }
  [data-testid="stMarkdownContainer"] blockquote {
    border-left: 3px solid rgba(139, 92, 246, .5);
    background: rgba(139, 92, 246, .06);
    border-radius: 0 10px 10px 0;
    padding: .6rem 1rem;
    margin: 1rem 0;
  }

  /* ---------- alerts / misc ---------- */
  [data-testid="stAlert"] {
    border-radius: 12px;
    border: 1px solid var(--rg-border);
  }
  [data-testid="stSpinner"] { color: #c4b5fd; }

  .rg-footer {
    text-align: center;
    color: #4b5563;
    font-size: .8rem;
    padding: 3rem 0 0;
  }
  .rg-hint { color: var(--rg-muted); font-size: .88rem; }

  /* ---------- empty-state steps ---------- */
  .rg-steps {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .75rem;
    margin-top: .25rem;
  }
  .rg-step {
    padding: 1rem 1.05rem;
    border-radius: 14px;
    border: 1px solid var(--rg-border);
    background: rgba(255, 255, 255, .025);
    transition: border-color .22s var(--rg-ease), background .22s var(--rg-ease), transform .22s var(--rg-ease);
  }
  .rg-step:hover {
    border-color: rgba(139, 92, 246, .4);
    background: rgba(139, 92, 246, .06);
    transform: translateY(-2px);
  }
  .rg-step .n {
    font-size: .68rem;
    font-weight: 700;
    letter-spacing: .14em;
    color: #a78bfa;
  }
  .rg-step h4 {
    margin: .35rem 0 .3rem;
    font-size: .95rem;
    font-weight: 650;
    color: #f1f5f9;
  }
  .rg-step p {
    margin: 0;
    font-size: .86rem;
    line-height: 1.55;
    color: var(--rg-muted);
  }

  /* ---------- scrollbar ---------- */
  ::-webkit-scrollbar { width: 10px; height: 10px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, .12);
    border-radius: 8px;
    border: 2px solid transparent;
    background-clip: content-box;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, .22);
    background-clip: content-box;
  }

  /* ---------- accessibility ---------- */
  button:focus-visible,
  [data-testid="stTab"]:focus-visible,
  [data-testid="stRadioOption"]:focus-visible {
    outline: 2px solid rgba(139, 92, 246, .8);
    outline-offset: 2px;
  }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: .001ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: .001ms !important;
    }
  }

  /* ---------- small screens ---------- */
  @media (max-width: 760px) {
    .block-container {
      padding-left: .75rem !important;
      padding-right: .75rem !important;
      padding-top: 1rem !important;
    }
    .rg-header { padding: 1.7rem .5rem 1rem; border-radius: 20px; }
    .rg-title { font-size: 2rem; }
    .rg-tagline { font-size: .92rem; }
    .st-key-input_card,
    .st-key-result_card {
      padding: 1.1rem 1rem 1rem !important;
      border-radius: 18px !important;
    }
    .st-key-result_card::before { display: none; }
    [data-testid="stTabs"] [role="tablist"] { width: 100%; }
    [data-testid="stTabs"] [data-testid="stTab"] { flex: 1; text-align: center; }
    .rg-steps { grid-template-columns: 1fr; }
  }
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
<p class="rg-section">How it works</p>
<div class="rg-steps">
  <div class="rg-step">
    <div class="n">STEP 01</div>
    <h4>Point it at code</h4>
    <p>Paste a snippet, upload files or a .zip, or drop a public GitHub URL.</p>
  </div>
  <div class="rg-step">
    <div class="n">STEP 02</div>
    <h4>Pick a lens</h4>
    <p>Project overview, code walkthrough, where to start, or a code review.</p>
  </div>
  <div class="rg-step">
    <div class="n">STEP 03</div>
    <h4>Keep asking</h4>
    <p>Follow-up questions keep the code in context. Export it all as Markdown.</p>
  </div>
</div>
<p class="rg-hint" style="margin-top:1rem">
Everything runs on your machine — nothing you paste leaves this computer.
</p>
""",
            unsafe_allow_html=True,
        )

st.markdown(
    f'<div class="rg-footer">{config.APP_NAME} v{config.VERSION} · runs on '
    f'Ollama · your code never leaves this machine</div>',
    unsafe_allow_html=True,
)
