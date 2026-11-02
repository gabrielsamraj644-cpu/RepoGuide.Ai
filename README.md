# 📚 RepoGuide AI

**Understand any codebase, one step at a time.**

RepoGuide AI takes code you point it at — a snippet, a folder, a `.zip`, or a public
GitHub repository — and explains it in plain English using an **open-weight model
running locally** through [Ollama](https://ollama.com).

No API keys. No account. No code leaves your machine.

---

## Why

Drop a first-year student into an unfamiliar repository and the usual outcome is
panic: 40 files, no map, no idea where to start. RepoGuide reads the code and
answers the four questions that actually matter:

| Mode | Question it answers |
| --- | --- |
| 🧭 **Project overview** | What is this thing and what problem does it solve? |
| 🔍 **Code walkthrough** | What does this code do, step by step? |
| 🏁 **Where to start** | What do I open first, and what's my first change? |
| 🛠️ **Code review** | What's broken, risky, or worth improving? |

Then you can **keep asking follow-up questions** in the same conversation.

---

## Features

- **Three ways in** — paste text, upload files/`.zip`, or paste a public GitHub URL.
- **Smart ingestion** — skips `node_modules`, `.git`, binaries and build output;
  strips the wrapper folder from GitHub archives.
- **Context budgeting** — Ollama's default context window is tiny. RepoGuide sizes
  the input to the window you choose, prioritises READMEs and top-level files, and
  tells you exactly what it left out instead of silently cutting your code.
- **Live streaming** — answers appear token by token, so a 60-second generation
  doesn't feel broken.
- **Follow-up chat** — the conversation keeps the analysed code in context.
- **Honest model badge** — shows the model you actually selected, not a hardcoded one.
- **Export** — download the whole analysis as Markdown.
- **Any Ollama model** — Gemma, Qwen, Llama, Mistral, DeepSeek, whatever you've pulled.

---

## Quick start

### 1. Ollama

Install from [ollama.com](https://ollama.com), then pull an open-weight model:

```bash
ollama pull gemma          # small, friendly default
# or, better at code:
ollama pull qwen2.5-coder:7b
```

Make sure Ollama is running (`ollama serve`, or just open the app).

### 2. Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
streamlit run app.py
```

Opens on <http://localhost:8501>.

---

## How it works

```
app.py                  Streamlit UI — layout, state, streaming
repoguide/
├── config.py           Every tunable value in one place
├── ollama.py           Tiny HTTP client for the Ollama API
├── prompts.py          Personas and output shapes (the actual "product")
└── ingest.py           Files / zips / GitHub → clean, budgeted text
```

The pipeline:

1. **Collect** — pasted text, uploaded files, a zip, or a GitHub archive.
2. **Filter** — drop binaries, build folders, and anything absurdly large.
3. **Budget** — pack as many files as fit into `context window − 28% for the answer`.
4. **Prompt** — wrap the code in a mode-specific persona with a required outline.
5. **Stream** — print the reply as it's generated; keep it for follow-ups.

Because the model is local, the only limit on how much you analyse is your RAM.

---

## Configuration

Environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `REPOGUIDE_OLLAMA_HOST` | `http://localhost:11434` | Point at a remote Ollama box |
| `REPOGUIDE_READ_TIMEOUT` | `600` | Seconds to wait for a generation |

Everything else — context size, temperature, file limits, recommended models —
lives in [`repoguide/config.py`](repoguide/config.py).

**Running out of memory?** Lower *Context window* in the sidebar's Advanced panel,
or switch to a smaller model.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| "Could not reach Ollama" | Start Ollama: `ollama serve` |
| "Model … is not installed" | `ollama pull <model>` |
| Answers stop mid-sentence | Context window too small — raise it in Advanced |
| Very slow first answer | Normal — a 5 GB model is loading into RAM. Later answers reuse it. |
| Empty or nonsense replies | Try a larger model; small models struggle with long code |

---

## Roadmap

- [ ] Token-aware budgeting (currently a character estimate)
- [ ] Remember which repository you're on between questions
- [ ] Diff mode — explain a pull request
- [ ] Dependency graph of the repo
- [ ] Local history of past analyses

---

## License

MIT — do what you like with it.
