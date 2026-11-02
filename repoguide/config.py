"""Central configuration for RepoGuide AI.

Everything tunable lives here so the rest of the codebase stays readable.
Values can be overridden with environment variables where it makes sense.
"""

from __future__ import annotations

import os

# --------------------------------------------------------------------------
# App identity
# --------------------------------------------------------------------------
APP_NAME = "RepoGuide AI"
APP_ICON = "📚"
VERSION = "2.0.0"

# --------------------------------------------------------------------------
# Ollama connection
# --------------------------------------------------------------------------
# Point this at a remote Ollama box with REPOGUIDE_OLLAMA_HOST if you want.
OLLAMA_HOST = os.getenv("REPOGUIDE_OLLAMA_HOST", "http://localhost:11434").rstrip("/")

# How long to wait for a single generation, in seconds (read timeout).
READ_TIMEOUT = int(os.getenv("REPOGUIDE_READ_TIMEOUT", "600"))

# Keep the model warm between prompts. Reloading a 5 GB model is slow.
KEEP_ALIVE = "15m"

# --------------------------------------------------------------------------
# Context budgeting
# --------------------------------------------------------------------------
# Ollama's default context is tiny (2-4k). We set it explicitly, because
# otherwise a moderately sized file silently gets cut off mid-function.
DEFAULT_NUM_CTX = 8192
NUM_CTX_CHOICES = [2048, 4096, 8192, 16384, 32768]

# Rough chars-per-token. 3.6 is deliberately conservative for code, which
# tokenises worse than prose.
CHARS_PER_TOKEN = 3.6

# Fraction of the context window reserved for the *answer* (not the input).
ANSWER_RESERVE = 0.28

# --------------------------------------------------------------------------
# Ingestion limits
# --------------------------------------------------------------------------
MAX_FILE_BYTES = 200_000        # skip any single file bigger than this
MAX_FILES = 120                 # stop after this many usable files
MAX_TOTAL_CHARS = 900_000       # hard cap on everything we hold in memory
MAX_ZIP_BYTES = 40 * 1024 * 1024
GITHUB_TIMEOUT = 45

# Directories that are never useful to explain.
SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".venv", "venv",
    "env", ".env", "dist", "build", ".next", ".nuxt", "target", "bin", "obj",
    "vendor", ".idea", ".vscode", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "coverage", "htmlcov", ".terraform", "Pods", ".gradle", ".tox", "site-packages",
}

# File extensions we consider source code / docs.
CODE_EXTENSIONS = {
    ".py", ".pyi", ".ipynb", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".java", ".kt", ".kts", ".scala", ".go", ".rs", ".rb", ".php", ".swift",
    ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".cs", ".m", ".r", ".jl",
    ".lua", ".pl", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".sql",
    ".html", ".htm", ".css", ".scss", ".sass", ".less", ".vue", ".svelte",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env.example",
    ".md", ".mdx", ".rst", ".txt", ".tf", ".dockerfile", ".gradle", ".cmake",
}

# Files with no extension that are still worth reading.
CODE_FILENAMES = {
    "dockerfile", "makefile", "procfile", "gemfile", "rakefile", "requirements",
    "license", "readme", "changelog", "contributing", "authors", "notice",
}

# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
# All of these are open-weight models you pull with Ollama. RepoGuide never
# calls a closed API - everything runs on your machine.
RECOMMENDED_MODELS = [
    {
        "tag": "qwen2.5-coder:7b",
        "label": "Qwen2.5 Coder 7B",
        "why": "Best all-round code explainer. Apache-2.0. ~4.7 GB.",
        "needs_vram": "≈5 GB RAM",
    },
    {
        "tag": "llama3.1:8b",
        "label": "Llama 3.1 8B",
        "why": "Strong general reasoning, good at explaining concepts. ~4.9 GB.",
        "needs_vram": "≈6 GB RAM",
    },
    {
        "tag": "gemma:latest",
        "label": "Gemma",
        "why": "Lightweight and friendly. Good default if you're low on RAM.",
        "needs_vram": "≈5 GB RAM",
    },
]
