# HUD‑CLI — A Terminal AI “Heads‑Up Display” for Coding

> Vendor‑neutral, multi‑provider CLI agent. Read/write files safely, propose diffs, commit changes, run dependency installs (with confirmation), and talk to tools via MCP. Built to feel like the best 0.1% of AI CLIs.

- **Providers:** OpenAI‑compatible, Anthropic (Claude), Google Gemini (chat today; tool calling next phase)
- **Editing:** `/edit` proposes a full‑file rewrite → shows a **unified diff** → asks to apply → commits via `/commit`
- **Files & Safety:** explicit **workspace roots**, size limits, audit log
- **Git:** `/diff`, `/commit`, `/revert`
- **Shell:** `/exec` with confirmation + logging
- **Deps:** `/deps` detects manifests and offers install commands
- **MCP:** list and call tools; filesystem/browser servers next phase

---

## Contents
- [Quick Start](#quick-start)
- [Configuration](#-configuration)
- [Safety Model](#-safety-model)
- [CLI Commands](#-cli-commands)
  - [Classic Chat CLI (`cli/gpt_cli.py`)](#classic-chat-cli-cligpt_clipypy)
  - [HUD CLI (advanced) (`cli/hud_cli.py`)](#hud-cli-advanced-clihud_clipypy)
- [MCP Usage](#-mcp-usage)
- [Dependency Bootstrapper](#-dependency-bootstrapper)
- [Audit Log](#-audit-log)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#license)

---

## Quick Start

### 1) Install
```bash
# from repo root
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 2) Configure
Copy the example and fill your keys:
```bash
cp .env.example .env
```

Supported providers (set in `.env` or environment variables):

```dotenv
# OpenAI-compatible (default)
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1

# Azure OpenAI (also works via OpenAI-compatible endpoints)
# OPENAI_API_KEY=...
# OPENAI_BASE_URL=https://{your-resource}.openai.azure.com/openai/deployments/{deployment}/extensions

# Anthropic Claude (Phase 2 chat)
ANTHROPIC_API_KEY=...
ANTHROPIC_VERSION=2023-06-01

# Google Gemini (Phase 2 chat)
GEMINI_API_KEY=...
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta

# CLI profile defaults
HUD_PROVIDER=openai       # openai|anthropic|gemini
HUD_MODEL=gpt-4o-mini     # change per your provider
```

### 3) Run
**Classic chat CLI:**
```bash
python cli/gpt_cli.py
```

**HUD CLI (advanced):**
```bash
python cli/hud_cli.py
/roots add .    # allow current directory
/status
```

---

## 🔧 Configuration

The HUD CLI stores its state at `~/.gpt_hud/config.yaml`:

```yaml
active_profile: default
profiles:
  default:
    provider: openai
    model: gpt-4o-mini
    roots:
      - /absolute/path/you/allowed
```

- Change provider/model here or via env vars.
- **Roots** define where the CLI can read/write. You can add more with `/roots add <path>`.

---

## 🛡️ Safety Model

- **Workspace roots only.** All file reads/writes are restricted to directories you explicitly add.
- **Confirmation prompts.** `/edit` shows a diff before applying; `/exec` asks before running commands.
- **Git guardrails.** Use `/diff`, `/commit`, `/revert` to review/undo.
- **Audit log.** Every mutation is appended to `~/.gpt_hud/audit.log`.

> You are always in control. Nothing runs without your consent.

---

## 🖥️ CLI Commands

### Classic Chat CLI (`cli/gpt_cli.py`)

Core chat REPL with utility commands (yours may include a subset depending on branch):

- `/system <text>` – set/print system prompt
- `/pwd`, `/ls [path]` – quick navigation
- `/read <path>` – print a file
- `/attach <path>` – attach a file to the next prompt
- `/attachments` – list attachments
- `/detach <index|all>` – remove attachment(s)
- `/mcp.tools` – list MCP tools available
- `/mcp.call {"name":"toolName","arguments":{...}}` – call an MCP tool
- `/status` – token/latency/cost HUD (if enabled)
- `/clear` – clear chat
- `/save` – save transcript
- `/exit` – quit

> Tip: The classic CLI focuses on fast prompting and manual MCP calls.

---

### HUD CLI (advanced) (`cli/hud_cli.py`)

A more “agentic” workflow with safety rails.

| Command | What it does |
|---|---|
| `/status` | Show provider, model, roots, git state |
| `/roots list` / `/roots add <path>` | Manage allowed workspace directories |
| `/open <path>` | Read a file (UTF‑8, size‑limited) |
| `/write <path> {"content":"..."}` | Overwrite/create a file |
| `/edit <path> <instruction...>` | LLM proposes a full‑file rewrite → unified diff → confirm apply |
| `/diff <path>` | `git diff` for a path |
| `/commit <message>` | Stage & commit all changes |
| `/revert <path>` | Restore file from last commit |
| `/deps` | Detect dependency manifests and offer to run installers |
| `/exec <command>` | Confirm‑gated shell execution with logging |
| *(anything else)* | Sends a normal chat to the model |

**Edit flow example:**
```
/edit README.md Tighten the intro and add a Quick Start
# review diff
Apply this patch? [y/N]: y
/commit docs: refresh README
```

---

## 🔌 MCP Usage

There’s a sample **Playwright MCP server** in `servers/mcp-playwright-server.mjs`. Start it separately (Node 20+):

```bash
node servers/mcp-playwright-server.mjs
```

From the CLI:
```
/mcp.tools
/mcp.call {"name":"open_url","arguments":{"url":"https://example.com"}}
```

> Phase 3 adds **auto‑discovery** and **model‑initiated tool use** (no manual `/mcp.call` needed).

---

## 📦 Dependency Bootstrapper

`/deps` scans for common manifests and proposes commands (you confirm before running):

- `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
- `poetry install`
- `npm install` / `pnpm install` / `yarn install`

---

## 🧾 Audit Log

All mutating actions are written to `~/.gpt_hud/audit.log`, e.g.
```
2025-08-13T20:05:33Z	edit-apply	README.md	applied diff
```

---

## 🧰 Troubleshooting

- **Python:** Use 3.10+ and a fresh venv.  
- **Windows:** Run in PowerShell; if you see mojibake, set UTF‑8: `chcp 65001` (or just use Windows Terminal).  
- **Auth:** If calls fail, verify `.env` and `OPENAI_BASE_URL` or provider‑specific keys.  
- **Git:** Initialize a repo to use `/diff`/`/commit`: `git init`.  
- **MCP:** Ensure the server process is actually running; tools won’t appear otherwise.

---

## 🗺️ Roadmap

- **Phase 3:** Model‑initiated tool/function calling (OpenAI tools first, then Claude/Gemini), MCP auto‑tools, diff‑hunk apply, per‑project profiles.
- **Phase 4:** Richer TUI, test suite, package releases.

---

## Contributing

- Keep PRs small and reviewable.  
- Use `/edit` to propose changes and `/commit` to capture intent.  
- Add tests/docs where useful.

## License

MIT (or your choice). See `LICENSE`.
