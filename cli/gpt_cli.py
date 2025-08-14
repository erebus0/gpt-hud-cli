import os
import sys
import json
import time
import uuid
import argparse
from pathlib import Path

import requests
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.table import Table
from rich.prompt import Prompt
from rich.rule import Rule

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---- MCP tiny client --------------------------------------------------------
from mcp_client import MCPClient  # make sure file is named mcp_client.py

console = Console()

# ---- Provider / ENV ---------------------------------------------------------
PROVIDER = (os.getenv("PROVIDER") or "azure").strip().lower()

# Azure OpenAI
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_DEPLOY = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_VER = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

# OpenAI-compatible (optional)
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# MCP
MCP_CMD = os.getenv("MCP_CMD")  # e.g. "node mcp-playwright-server.mjs"
MCP_ENDPOINTS = [e.strip() for e in (os.getenv("MCP_ENDPOINTS") or "").split(",") if e.strip()]

# Pricing (USD per 1k tokens). Keep zeros if you don’t want estimates.
PRICES = {
    "gpt-5-chat-latest": (0.0, 0.0, 0.0),
    "gpt-4o-mini": (0.0, 0.0, 0.0),
}

# File helpers config
MAX_ATTACH_BYTES = 300_000
TEXT_EXTS = {
    ".txt", ".md", ".py", ".json", ".yaml", ".yml", ".toml", ".js", ".ts",
    ".html", ".css", ".sh", ".bat", ".ps1", ".sql", ".csv"
}

# ---- Small utils ------------------------------------------------------------
def provider_ok():
    if PROVIDER == "azure":
        return bool(AZURE_ENDPOINT and AZURE_KEY and AZURE_DEPLOY)
    if PROVIDER == "openai":
        return bool(OPENAI_BASE_URL and OPENAI_API_KEY and OPENAI_MODEL)
    return False


def provider_panel():
    name = "Azure OpenAI" if PROVIDER == "azure" else "OpenAI-compatible"
    ok = provider_ok()
    txt = f"[b]provider[/b]={PROVIDER}\n[b]auth[/b]={'set' if ok else 'missing'}"
    return Panel(
        txt,
        title=f"{name} " + ("[green]OK" if ok else "[red]NOT READY"),
        border_style="green" if ok else "red",
    )


def mcp_panel(message=None):
    if message:
        return Panel(message, title="MCP", border_style="green")
    if not MCP_ENDPOINTS:
        return Panel(
            "No MCP health URLs configured.\nSet MCP_ENDPOINTS=http://127.0.0.1:8931/health",
            title="MCP",
            border_style="yellow",
        )
    rows = []
    healthy = True
    for ep in MCP_ENDPOINTS:
        try:
            r = requests.get(ep, timeout=2)
            ok = 200 <= r.status_code < 300
            rows.append(f"{ep} : {'OK' if ok else f'FAIL({r.status_code})'}")
            healthy &= ok
        except Exception:
            rows.append(f"{ep} : FAIL")
            healthy = False
    return Panel("\n".join(rows), title="MCP", border_style="green" if healthy else "yellow")


def banner(mcp_message=None):
    console.print(Rule("[bold cyan]GPT-HUD[/bold cyan]"))
    console.print(
        Panel.fit(
            "Commands: /system, /pwd, /ls, /read, /attach, /attachments, /detach, "
            "/mcp.tools, /mcp.call <tool> {json}, /clear, /status, /save, /exit",
            border_style="cyan",
        )
    )
    console.print(Columns([provider_panel(), mcp_panel(mcp_message)]))


def estimate_cost(model, pt, ct, cached):
    p_in, p_out, p_cache = PRICES.get(model, (0.0, 0.0, 0.0))
    billable_prompt = max(0, (pt or 0) - (cached or 0))
    return round((billable_prompt / 1000) * p_in + (ct or 0) / 1000 * p_out + (cached or 0) / 1000 * p_cache, 6)


def summarize_usage(usage_obj, fallback_model):
    if not isinstance(usage_obj, dict):
        return (fallback_model, 0, 0, 0, 0)
    pt = usage_obj.get("prompt_tokens", 0)
    ct = usage_obj.get("completion_tokens", 0)
    cached = 0
    ptd = usage_obj.get("prompt_tokens_details")
    if isinstance(ptd, dict):
        cached = ptd.get("cached_tokens", 0)
    else:
        cached = usage_obj.get("cached_tokens", 0) or 0
    total = usage_obj.get("total_tokens", pt + ct)
    model = usage_obj.get("model") or fallback_model
    return (model, pt, ct, cached, total)


def usage_table(rows):
    t = Table(title="Session Usage", expand=True)
    t.add_column("Model")
    t.add_column("Prompt", justify="right")
    t.add_column("Completion", justify="right")
    t.add_column("Cached", justify="right")
    t.add_column("Total", justify="right")
    t.add_column("Latency", justify="right")
    t.add_column("Est. Cost", justify="right")
    agg = {"pt": 0, "ct": 0, "cached": 0, "total": 0, "lat": 0.0, "cost": 0.0}
    for (m, pt, ct, ca, tt, lat, cost) in rows:
        t.add_row(m, str(pt), str(ct), str(ca), str(tt), f"{lat:.2f}s", f"${cost}")
        agg["pt"] += pt
        agg["ct"] += ct
        agg["cached"] += ca
        agg["total"] += tt
        agg["lat"] += lat
        agg["cost"] += cost
    t.add_row(
        "[b]TOTAL[/b]",
        str(agg["pt"]),
        str(agg["ct"]),
        str(agg["cached"]),
        str(agg["total"]),
        f"{agg['lat']:.2f}s",
        f"${round(agg['cost'], 6)}",
    )
    return t

# ---- Provider adapters -------------------------------------------------------
def send_chat(messages, stream=True, temperature=0.2, max_tokens=512):
    if PROVIDER == "azure":
        if not provider_ok():
            raise RuntimeError("Azure env incomplete.")
        url = f"{AZURE_ENDPOINT}/openai/deployments/{AZURE_DEPLOY}/chat/completions?api-version={AZURE_VER}"
        headers = {"api-key": AZURE_KEY, "Content-Type": "application/json"}
        body = {"messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": stream}
        r = requests.post(url, headers=headers, json=body, stream=stream, timeout=300)
        r.raise_for_status()
        return r

    if PROVIDER == "openai":
        if not provider_ok():
            raise RuntimeError("OpenAI env incomplete.")
        url = f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        body = {"model": OPENAI_MODEL, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": stream}
        r = requests.post(url, headers=headers, json=body, stream=stream, timeout=300)
        r.raise_for_status()
        return r

    raise RuntimeError(f"Unsupported PROVIDER={PROVIDER}")

# ---- File helpers ------------------------------------------------------------
def ls(path=None):
    p = Path(path) if path else Path.cwd()
    if not p.exists():
        return f"Path not found: {p}"
    items = []
    for x in sorted(p.iterdir()):
        items.append(f"{x.name}{'/' if x.is_dir() else ''}")
    return "\n".join(items) or "(empty)"


def read_text_file(path):
    p = Path(path)
    if not p.exists():
        return None, f"File not found: {path}"
    if p.suffix and p.suffix.lower() not in TEXT_EXTS:
        return None, f"Refusing non-text file (.{p.suffix}). Add to TEXT_EXTS if needed."
    data = p.read_bytes()
    if len(data) > MAX_ATTACH_BYTES:
        return None, f"File too large ({len(data)} bytes) > {MAX_ATTACH_BYTES}."
    try:
        return data.decode("utf-8", errors="ignore"), None
    except Exception as e:
        return None, f"Decode error: {e}"

# ---- REPL --------------------------------------------------------------------
def repl():
    # MCP auto-spawn (stdio)
    mcp = None
    mcp_banner_msg = None
    if MCP_CMD:
        try:
            mcp = MCPClient(MCP_CMD)
            mcp.start()
            time.sleep(0.4)  # give it a moment to boot
            try:
                tools = mcp.list_tools()
                names = [t.get("name", "?") for t in tools]
                mcp_banner_msg = "spawned • tools: " + (", ".join(names) or "(none)")
            except Exception as e:
                mcp_banner_msg = f"spawned • tools: (error listing: {e})"
        except Exception as e:
            mcp_banner_msg = f"not started: {e}"

    banner(mcp_banner_msg)
    console.print()

    if not provider_ok():
        console.print("[yellow]Provider not fully configured. MCP commands still work.[/yellow]")

    system_msg = None
    history = []
    transcript = []
    attachments = {}
    usage_rows = []
    session_id = uuid.uuid4().hex[:8]

    def build_messages(user_text):
        msgs = []
        if system_msg:
            msgs.append({"role": "system", "content": system_msg})
        for p, content in attachments.items():
            msgs.append({"role": "user", "content": f"[file:{p}]\n{content}"})
        msgs.extend(history[-20:])
        msgs.append({"role": "user", "content": user_text})
        return msgs

    while True:
        try:
            user = Prompt.ask("[bold cyan]You[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye.[/dim]")
            break

        if not user:
            continue
        low = user.lower()

        # -------- Commands
        if low in ("/exit", "exit", "quit", "/quit"):
            break
        if low == "/clear":
            history.clear()
            console.print("✓ history cleared.")
            continue
        if low == "/status":
            banner(mcp_banner_msg)
            continue
        if user.startswith("/system "):
            system_msg = user[len("/system "):].strip()
            console.print("✓ system prompt set.")
            continue
        if low == "/pwd":
            console.print(str(Path.cwd()))
            continue
        if user.startswith("/ls"):
            arg = user.split(" ", 1)[1].strip() if " " in user else None
            console.print(ls(arg))
            continue
        if user.startswith("/read "):
            path = user.split(" ", 1)[1].strip()
            content, err = read_text_file(path)
            console.print(Panel.fit(content[:1000], title=f"Preview: {path}", border_style="blue") if not err else f"[red]{err}[/red]")
            continue
        if user.startswith("/attach "):
            path = user.split(" ", 1)[1].strip()
            content, err = read_text_file(path)
            if err:
                console.print(f"[red]{err}[/red]")
            else:
                attachments[path] = content
                console.print(f"✓ attached {path} ({len(content)} bytes)")
            continue
        if low == "/attachments":
            if not attachments:
                console.print("(no attachments)")
            else:
                for p, c in attachments.items():
                    console.print(f"- {p} [{len(c)} bytes]")
            continue
        if user.startswith("/detach "):
            path = user.split(" ", 1)[1].strip()
            console.print(f"{'✓ detached' if attachments.pop(path, None) is not None else '(not attached)'} {path}")
            continue

        # -------- MCP commands
        if low == "/mcp.tools":
            if not mcp:
                console.print("[yellow]MCP not running. Set MCP_CMD in .env[/yellow]")
            else:
                try:
                    tools = mcp.list_tools()
                    if not tools:
                        console.print("(no tools)")
                    else:
                        for t in tools:
                            console.print(f"- {t.get('name','?')}: {t.get('description','')}")
                except Exception as e:
                    console.print(f"[red]tools/list failed: {e}[/red]")
            continue

        if user.startswith("/mcp.call "):
            if not mcp:
                console.print("[yellow]MCP not running. Set MCP_CMD in .env[/yellow]")
            else:
                try:
                    # /mcp.call <toolName> {jsonArgs}
                    parts = user.split(" ", 2)
                    if len(parts) < 2:
                        console.print("Usage: /mcp.call <toolName> {json args}")
                    else:
                        name = parts[1]
                        args = {}
                        if len(parts) == 3 and parts[2].strip():
                            args = json.loads(parts[2])
                        res = mcp.call_tool(name, args)
                        console.print(res)
                except Exception as e:
                    console.print(f"[red]tools/call failed: {e}[/red]")
            continue

        # -------- Chat send (only if provider configured)
        if not provider_ok():
            console.print("[yellow]Provider not configured; only MCP commands will work. Set PROVIDER/envs in .env[/yellow]")
            continue

        messages = build_messages(user)
        try:
            start = time.time()
            r = send_chat(messages, stream=True)
            console.print("[bold magenta]Assistant[/bold magenta]: ", end="")
            full = []
            usage_final = None
            for line in r.iter_lines():
                if not line:
                    continue
                if line.startswith(b"data: "):
                    chunk = line[6:].decode("utf-8").strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        ob = json.loads(chunk)
                        delta = ob["choices"][0]["delta"].get("content", "")
                        if delta:
                            full.append(delta)
                            console.print(delta, end="")
                        if "usage" in ob:
                            usage_final = ob["usage"]
                    except Exception:
                        pass
            console.print()
            assistant_text = "".join(full)
            history.append({"role": "user", "content": user})
            history.append({"role": "assistant", "content": assistant_text})
            transcript.append(("you", user))
            transcript.append(("assistant", assistant_text))

            model, pt, ct, cached, total = summarize_usage(
                usage_final,
                fallback_model=("gpt-5-chat-latest" if PROVIDER == "azure" else OPENAI_MODEL),
            )
            latency = time.time() - start
            cost = estimate_cost(model, pt, ct, cached)
            usage_rows.append((model, pt, ct, cached, total, latency, cost))

        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            body = ""
            try:
                body = e.response.text[:500]
            except Exception:
                pass
            console.print(f"[red]\nHTTP {status}: {body}[/red]")
        except Exception as ex:
            console.print(f"[red]\n{type(ex).__name__}: {ex}[/red]")

    # On exit: show usage and stop MCP
    if usage_rows:
        console.print(usage_table(usage_rows))
    if mcp:
        mcp.close()

# ---- One-shot ---------------------------------------------------------------
def run_once(args):
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    if args.messages_file:
        with open(args.messages_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            messages.extend(data["messages"] if isinstance(data, dict) and "messages" in data else data)
    else:
        messages.append({"role": "user", "content": args.prompt})
    r = send_chat(messages, stream=args.stream, temperature=args.temp, max_tokens=args.max_tokens)
    if args.stream:
        console.print("[bold magenta]Assistant[/bold magenta]: ", end="")
        usage_final = None
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith(b"data: "):
                chunk = line[6:].decode("utf-8").strip()
                if chunk == "[DONE]":
                    break
                try:
                    ob = json.loads(chunk)
                    delta = ob["choices"][0]["delta"].get("content", "")
                    if delta:
                        console.print(delta, end="")
                    if "usage" in ob:
                        usage_final = ob["usage"]
                except Exception:
                    pass
        console.print()
        if usage_final:
            model, pt, ct, cached, total = summarize_usage(
                usage_final,
                fallback_model=("gpt-5-chat-latest" if PROVIDER == "azure" else OPENAI_MODEL),
            )
            cost = estimate_cost(model, pt, ct, cached)
            t = usage_table([(model, pt, ct, cached, total, 0.0, cost)])
            console.print(t)
    else:
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        console.print(Panel.fit(content, title="Assistant", border_style="magenta"))

# ---- Main -------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser("gpt-hud")
    ap.add_argument("--prompt")
    ap.add_argument("--messages-file")
    ap.add_argument("--system")
    ap.add_argument("--stream", action="store_true")
    ap.add_argument("--temp", type=float, default=0.2)
    ap.add_argument("--max-tokens", type=int, default=512)
    args = ap.parse_args()

    if not args.prompt and not args.messages_file:
        return repl()
    if not provider_ok():
        console.print("[red]Provider not configured for one-shot. Set .env or use REPL for MCP-only.[/red]")
        sys.exit(2)
    return run_once(args)

if __name__ == "__main__":
    main()
