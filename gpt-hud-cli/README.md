# GPT-HUD CLI

A clean, terminal-first chat CLI with a simple HUD, file helpers, and **optional** MCP tool support.

## Features
- Azure OpenAI or any OpenAI-compatible endpoint
- TUI with Rich (commands: `/system`, `/pwd`, `/ls`, `/read`, `/attach`, `/mcp.tools`, `/mcp.call`, `/clear`, `/status`, `/save`, `/exit`)
- File attach/preview from the current directory
- Usage table at end of session (tokens, latency, est. cost)
- Optional MCP (Model Context Protocol) over stdio; sample Playwright server included

## Quick start
```bash
git clone YOUR_REPO_URL gpt-hud-cli
cd gpt-hud-cli
./install.sh
cp .env.example .env
# fill in Azure or OpenAI env vars
source .venv/bin/activate
python cli/gpt_cli.py
