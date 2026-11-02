"""Turning messy real-world input into one clean block of text.

Three sources feed in:
  * pasted text,
  * uploaded files / a .zip,
  * a public GitHub repository URL.

All of them end up as a list of `FileEntry` objects. `render()` then decides
what actually fits into the model's context window, and says so honestly.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Iterable

import requests

from . import config

# Extension -> fence language for Markdown code blocks.
LANG_BY_EXT = {
    ".py": "python", ".pyi": "python", ".ipynb": "json",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".jsx": "jsx", ".ts": "typescript", ".tsx": "tsx",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin", ".scala": "scala",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
    ".swift": "swift", ".m": "objectivec", ".r": "r", ".jl": "julia",
    ".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp",
    ".hpp": "cpp", ".cs": "csharp", ".lua": "lua", ".pl": "perl",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash", ".ps1": "powershell",
    ".bat": "batch", ".sql": "sql",
    ".html": "html", ".htm": "html", ".css": "css", ".scss": "scss",
    ".sass": "sass", ".less": "less", ".vue": "vue", ".svelte": "svelte",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".ini": "ini", ".cfg": "ini", ".md": "markdown", ".mdx": "markdown",
    ".rst": "rst", ".txt": "text", ".tf": "hcl", ".cmake": "cmake",
    ".gradle": "groovy",
}


@dataclass
class FileEntry:
    path: str
    content: str

    @property
    def lang(self) -> str:
        return LANG_BY_EXT.get(PurePosixPath(self.path).suffix.lower(), "")

    @property
    def is_doc(self) -> bool:
        return PurePosixPath(self.path).suffix.lower() in {".md", ".rst", ".txt"}

    @property
    def depth(self) -> int:
        return self.path.count("/")


@dataclass
class Ingest:
    """Everything we managed to read, plus what we skipped and why."""

    entries: list[FileEntry] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    source: str = ""

    @property
    def total_chars(self) -> int:
        return sum(len(e.content) for e in self.entries)

    def __bool__(self) -> bool:
        return bool(self.entries)


@dataclass
class Context:
    """The budgeted text handed to the model."""

    text: str
    included: int
    dropped: int
    chars: int
    truncated: bool

    @property
    def approx_tokens(self) -> int:
        return int(self.chars / config.CHARS_PER_TOKEN)


# --------------------------------------------------------------------------
# Filtering / decoding
# --------------------------------------------------------------------------
def _is_useful(path: str) -> bool:
    parts = PurePosixPath(path).parts
    if any(part in config.SKIP_DIRS for part in parts[:-1]):
        return False
    name = parts[-1].lower()
    if name.startswith("."):
        # allow a couple of meaningful dotfiles
        return name in {".gitignore", ".env.example", ".dockerignore"}
    if PurePosixPath(name).suffix in config.CODE_EXTENSIONS:
        return True
    return name in config.CODE_FILENAMES or name.split(".")[0] in config.CODE_FILENAMES


def _decode(data: bytes) -> str | None:
    """Return text, or None when the bytes look binary."""
    if b"\x00" in data[:2048]:
        return None
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    try:
        return data.decode("latin-1")
    except UnicodeDecodeError:
        return None


def _add(ingest: Ingest, path: str, data: bytes) -> None:
    if len(ingest.entries) >= config.MAX_FILES:
        return
    if ingest.total_chars >= config.MAX_TOTAL_CHARS:
        return
    if len(data) > config.MAX_FILE_BYTES:
        ingest.skipped.append(f"{path} (too large: {len(data) // 1024} KB)")
        return
    text = _decode(data)
    if text is None or not text.strip():
        ingest.skipped.append(f"{path} (binary or empty)")
        return
    ingest.entries.append(FileEntry(path=path, content=text))


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------
def from_text(text: str, name: str = "pasted-snippet.txt") -> Ingest:
    ingest = Ingest(source="pasted text")
    if text and text.strip():
        _add(ingest, name, text.encode("utf-8"))
    return ingest


def from_uploads(files: Iterable) -> Ingest:
    """Accepts Streamlit UploadedFile objects (or anything with .name/.read)."""
    ingest = Ingest(source="uploaded files")
    for f in files:
        name = getattr(f, "name", "file")
        data = f.read() if hasattr(f, "read") else bytes(f)
        if name.lower().endswith(".zip"):
            _merge(ingest, _from_zip(data, name))
        else:
            _add(ingest, name, data)
    return ingest


def _merge(target: Ingest, other: Ingest) -> None:
    target.entries.extend(other.entries)
    target.skipped.extend(other.skipped)


def _from_zip(data: bytes, name: str = "archive.zip") -> Ingest:
    ingest = Ingest(source=f"zip: {name}")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        ingest.skipped.append(f"{name} (not a valid zip)")
        return ingest

    with archive:
        names = [n for n in archive.namelist() if not n.endswith("/")]
        # GitHub zips wrap everything in one top-level folder. Strip it.
        roots = {n.split("/")[0] for n in names}
        prefix = f"{roots.pop()}/" if len(roots) == 1 and all("/" in n for n in names) else ""

        for member in names:
            clean = member[len(prefix):] if prefix and member.startswith(prefix) else member
            if not _is_useful(clean):
                continue
            info = archive.getinfo(member)
            if info.file_size > config.MAX_FILE_BYTES:
                ingest.skipped.append(f"{clean} (too large)")
                continue
            try:
                with archive.open(member) as fh:
                    _add(ingest, clean, fh.read())
            except (KeyError, RuntimeError, zipfile.BadZipFile):
                ingest.skipped.append(f"{clean} (unreadable)")
    return ingest


def parse_github(url: str) -> tuple[str, str, str | None] | None:
    """'https://github.com/owner/repo' -> ('owner', 'repo', None).

    Handles `.git` suffixes, trailing slashes, query strings, and branch names
    that themselves contain slashes (`/tree/feat/login`).
    """
    cleaned = url.strip()
    cleaned = re.sub(r"^[a-zA-Z][\w+.-]*://", "", cleaned)   # strip scheme
    cleaned = re.sub(r"^www\.", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.split("?", 1)[0].split("#", 1)[0]

    segments = [s for s in cleaned.split("/") if s]
    if len(segments) < 3:
        return None
    if segments[0].lower() not in {"github.com", "gitlab.com"}:
        return None

    owner, repo = segments[1], segments[2]
    if repo.lower().endswith(".git"):
        repo = repo[:-4]

    branch: str | None = None
    if len(segments) >= 5 and segments[3] in {"tree", "blob"}:
        branch = "/".join(segments[4:])
        # `blob` URLs point at a file, not a branch tip
        if segments[3] == "blob" and branch:
            branch = branch.rsplit("/", 1)[0] or None

    if not owner or not repo:
        return None
    return owner, repo, branch


def from_github(url: str) -> Ingest:
    parsed = parse_github(url)
    if not parsed:
        ingest = Ingest(source=url)
        ingest.skipped.append("Not a recognisable GitHub URL (expected github.com/owner/repo)")
        return ingest

    owner, repo, branch = parsed
    ingest = Ingest(source=f"github: {owner}/{repo}")
    branches = [branch] if branch else ["main", "master"]
    last_error = ""

    for candidate in branches:
        archive_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{candidate}"
        try:
            with requests.get(archive_url, stream=True, timeout=config.GITHUB_TIMEOUT) as r:
                if r.status_code != 200:
                    last_error = f"HTTP {r.status_code} for branch '{candidate}'"
                    continue
                buffer = io.BytesIO()
                for chunk in r.iter_content(chunk_size=65536):
                    buffer.write(chunk)
                    if buffer.tell() > config.MAX_ZIP_BYTES:
                        ingest.skipped.append(
                            f"repository is larger than {config.MAX_ZIP_BYTES // 1024 // 1024} MB"
                        )
                        return ingest
                return _from_zip(buffer.getvalue(), f"{repo}.zip")
        except requests.RequestException as exc:
            last_error = str(exc)

    ingest.skipped.append(f"Could not download repository ({last_error})")
    return ingest


# --------------------------------------------------------------------------
# Budgeting
# --------------------------------------------------------------------------
def render(ingest: Ingest, max_chars: int) -> Context:
    """Fit as many files as possible into `max_chars`, docs and shallow
    files first, and report exactly what was left out."""
    if not ingest.entries:
        return Context("", 0, 0, 0, False)

    # README first (best overview), then shallow files, then alphabetical.
    ordered = sorted(
        ingest.entries,
        key=lambda e: (0 if e.is_doc else 1, e.depth, e.path.lower()),
    )

    blocks: list[str] = []
    used = 0
    included = 0
    dropped = 0
    truncated = False

    for entry in ordered:
        header = f"\n\n---\n### File: `{entry.path}`\n```{entry.lang}\n"
        footer = "\n```"
        block_len = len(header) + len(entry.content) + len(footer)
        remaining = max_chars - used

        if block_len <= remaining:
            blocks.append(f"{header}{entry.content}{footer}")
            used += block_len
            included += 1
            continue

        # Partial fit: keep the top of the file, it's usually the useful part
        # (imports, class/function signatures).
        room = remaining - len(header) - len(footer) - 120
        if room > 800:
            blocks.append(f"{header}{entry.content[:room]}\n\n# … [file truncated] …{footer}")
            used += room + len(header) + len(footer)
            included += 1
            truncated = True
        else:
            dropped += 1

    text = "".join(blocks).lstrip("\n")
    return Context(
        text=text,
        included=included,
        dropped=dropped,
        chars=len(text),
        truncated=truncated,
    )


def max_chars_for(num_ctx: int) -> int:
    """How many characters of source we can afford for a given context size."""
    input_tokens = num_ctx * (1 - config.ANSWER_RESERVE)
    return int(input_tokens * config.CHARS_PER_TOKEN)
