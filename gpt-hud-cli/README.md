# GPT-HUD CLI — Robust, Provider-Agnostic Dev Agent (Phase 2)

A fast, safe, *explainable* terminal assistant that can **read and write files**, propose **diffs**, **commit** changes, run **dependency bootstraps**, and (optionally) execute shell commands with confirmation prompts.

> This README is designed to be useful for both first‑time users and advanced practitioners. It also includes SEO‑friendly sections, headings, and keywords (CLI AI assistant, code editor agent, LLM devtools, Anthropic Claude, Google Gemini, OpenAI compatible, MCP, safe file editing).

---

## Quick start

```bash
git clone <your-repo-url>
cd gpt-hud-cli
pip install -r requirements.txt
python cli/hud_cli.py
```

### Configure a provider

Set environment variables or put them in `.env` (your existing flow still works):

```dotenv
# OpenAI-compatible (default)
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
HUD_PROVIDER=openai
HUD_MODEL=gpt-4o-mini

# Optional: Anthropic Claude (basic chat in Phase 2)
ANTHROPIC_API_KEY=...
ANTHROPIC_VERSION=2023-06-01

# Optional: Google Gemini (basic chat in Phase 2)
GEMINI_API_KEY=...
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
```

> Configuration is saved in `~/.gpt_hud/config.yaml`. You can create **profiles** later (e.g., `default`, `work`, `offline`) and switch models per project.

---

## Safety model (must read)

- **Workspace roots.** The CLI can only read/write inside directories you explicitly allow.
- **Confirmation prompts.** All shell commands (`/exec`) and edit patches (`/edit`) ask for consent.
- **Git integration.** Use `/diff`, `/commit`, `/revert` to audit and undo.
- **Audit log.** Every mutation is logged to `~/.gpt_hud/audit.log` with timestamps.

> This reduces risk while keeping the workflow fast. You are always in control.

---

## First run checklist

1. Start the CLI:
   ```bash
   python cli/hud_cli.py
   ```
2. Add a workspace root (current directory):
   ```
   /roots add .
   ```
3. Show status:
   ```
   /status
   ```
4. Read a file:
   ```
   /open README.md
   ```
5. Propose an edit and apply it:
   ```
   /edit README.md Rewrite the intro to be clearer
   # review the diff
   # answer prompt: Apply this patch? (y/N)
   ```
6. Commit:
   ```
   /commit docs: refresh README intro
   ```

---

## Commands

| Command | Purpose |
|---|---|
| `/status` | Show provider, model, roots, and git status |
| `/roots list` / `/roots add <path>` | Manage allowed workspace directories |
| `/open <path>` | Read and print a file (UTF‑8, size-limited) |
| `/write <path> {"content":"..."}` | Write/overwrite a file (within roots) |
| `/edit <path> <instruction...>` | Model proposes a full-file rewrite, shows a **unified diff**, and asks to apply |
| `/diff <path>` | Show `git diff` for a path |
| `/commit <message>` | Stage & commit all changes |
| `/revert <path>` | Checkout file from last commit |
| `/deps` | Detect dependency manifests and offer to run installer commands |
| `/exec <command>` | Run a shell command **with confirmation** |
| *(anything else)* | Sends chat to the model |

---

## Providers

- **OpenAI-compatible** backends fully supported for chat. (Tool/function calling to be added in a subsequent phase.)
- **Anthropic Claude** and **Google Gemini** supported for **basic chat**.
- You can switch via env vars, or by editing `~/.gpt_hud/config.yaml`.

> Goals: parity with Open Interpreter/Aider-level file operations and multi-provider support with **MCP** tool integration (filesystem, browser, db).

---

## Dependency bootstrapper

`/deps` looks for `requirements.txt`, `pyproject.toml`, `package.json`, `pnpm-lock.yaml`, `yarn.lock` and offers commands like:

- `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
- `poetry install`
- `npm install` / `pnpm install` / `yarn install`

Each command asks for confirmation before running.

---

## Audit log

All mutating actions append a line to `~/.gpt_hud/audit.log`:

```
2025-08-13T20:05:33Z  edit-apply   README.md    applied diff
```

---

## FAQ (for SEO and clarity)

### Is this like Open Interpreter or Aider?
It combines a clear **terminal UX** with safe **file editing** and **git** workflows. The goal is top-tier ergonomics with multi-provider support (OpenAI, Anthropic Claude, Google Gemini) and future **MCP** tool auto-discovery.

### Can it write anywhere on my machine?
No. It only writes under directories you add via `/roots add`. This is deliberate for safety.

### Does it run arbitrary shell commands?
Only with your confirmation (`/exec`). Every command is logged.

### Can it manage dependencies automatically?
`/deps` detects typical manifests and offers one-liners to set up environments — you confirm before execution.

### What about MCP (Model Context Protocol)?
Phase 3 will expose MCP tools as auto-discoverable actions so the model can request them (filesystem, browser, etc). Manual MCP usage from your existing client can still coexist.

---

## Contributing

- Create a feature branch.
- Use `/edit` for iterative changes, then `/commit`.
- Write tests and docs along the way.
- Keep PRs small and reviewable.

---

## Roadmap

- **Phase 3:** Tool/function calling across providers, MCP tool registry, browser/filesystem servers, resource roots, and policy prompts.
- **Phase 4:** Project profiles, richer TUI, inline diff hunks, tests, release packaging.

---

## License

MIT (or your choice). See `LICENSE`.

