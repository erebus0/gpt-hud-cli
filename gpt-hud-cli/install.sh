#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Python env
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r cli/requirements.txt

# Node deps (for optional servers)
npm install

echo "✅ Installed.
To run:
  cp .env.example .env   # then fill in keys
  source .venv/bin/activate
  python cli/gpt_cli.py
"
