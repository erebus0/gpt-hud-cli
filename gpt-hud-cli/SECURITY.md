
---

# 3) Initialize & push

```bash
mkdir -p gpt-hud-cli/cli gpt-hud-cli/servers
# paste files into place...

cd gpt-hud-cli
git init
git add .
git commit -m "feat: initial open-source GPT-HUD CLI with optional MCP"
git branch -M main
git remote add origin <YOUR_GITHUB_SSH_OR_HTTPS_URL>
git push -u origin main
