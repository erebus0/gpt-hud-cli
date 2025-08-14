import os, json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

from hudcli import config as cfg
from hudcli.providers import make_provider
from hudcli.ops import fileops, diffing, gitwrap
from hudcli.ops import shell as sh
from hudcli.ops import deps as depdet
from hudcli.ops import audit

console = Console()

SYS_EDIT_PROMPT = (
    "You are a meticulous code editor. When given a file's current text and a user instruction, "
    "return ONLY the fully rewritten file content. Do not include explanations or code fences."
)

def banner(conf: dict):
    prof = cfg.active_profile(conf)
    t = Table.grid(padding=1)
    t.add_column(style="cyan", justify="left")
    t.add_column(style="magenta")
    t.add_row("Profile", conf.get("active_profile"))
    t.add_row("Provider", f"{prof.get('provider')} @{prof.get('model')}")
    roots = prof.get("roots", [])
    t.add_row("Roots", "\n".join(roots) if roots else "(none) - /roots add <path>")
    console.print(Panel(t, title="HUD-CLI — Phase 2", border_style="cyan"))

def cmd_status(conf):
    prof = cfg.active_profile(conf)
    t = Table(title="Status", show_lines=False, expand=True)
    t.add_column("Key", style="cyan")
    t.add_column("Value", style="white")
    t.add_row("Provider", f"{prof.get('provider')} @{prof.get('model')}")
    t.add_row("Roots", "\n".join(prof.get("roots", [])) or "(none)")
    t.add_row("Git repo", "yes" if gitwrap.is_repo(os.getcwd()) else "no")
    if gitwrap.is_repo(os.getcwd()):
        t.add_row("Git status", gitwrap.status(os.getcwd()) or "(clean)")
    console.print(t)

def cmd_roots(conf, args):
    prof = cfg.active_profile(conf)
    if len(args)==0 or args[0]=="list":
        roots = prof.get("roots", [])
        for r in roots: console.print(f"- {r}")
        if not roots: console.print("(no roots)")
        return
    if args[0]=="add" and len(args)>=2:
        path = str(Path(args[1]).expanduser().resolve())
        cfg.ensure_root(conf, path)
        cfg.save(conf)
        console.print(f"added root: {path}")
        return
    console.print("Usage: /roots [list|add <path>]")

def cmd_open(conf, args):
    if not args: console.print("Usage: /open <path>"); return
    prof = cfg.active_profile(conf)
    txt, err = fileops.read_text(args[0], prof.get("roots", []))
    if err: console.print(f"[red]{err}[/red]"); return
    console.rule(args[0]); console.print(txt)

def cmd_write(conf, args):
    if len(args) < 2:
        console.print("Usage: /write <path> {json with 'content'}"); return
    path = args[0]
    try:
        payload = json.loads(" ".join(args[1:])); content = payload.get("content", "")
    except Exception: console.print("Invalid JSON payload"); return
    prof = cfg.active_profile(conf)
    err = fileops.write_text(path, content, prof.get("roots", []))
    if err: console.print(f"[red]{err}[/red]")
    else:
        audit.log("write", detail=f"{len(content)} bytes", path=path)
        console.print(f"[green]wrote[/green] {path} ({len(content)} bytes)")

def cmd_diff(conf, args):
    if not args: console.print("Usage: /diff <path>"); return
    out = gitwrap.diff(args[0], cwd=os.getcwd())
    console.print(out or "(no changes)")

def cmd_commit(conf, args):
    msg = " ".join(args) or "chore: HUD apply"
    console.print(gitwrap.add_all())
    console.print(gitwrap.commit(msg))

def cmd_revert(conf, args):
    if not args: console.print("Usage: /revert <path>"); return
    console.print(gitwrap.revert(args[0]))

def do_chat(conf, prompt: str):
    prof = cfg.active_profile(conf)
    provider = make_provider(prof.get("provider"), prof.get("model"))
    messages = [{"role":"system","content":"You are a careful coding assistant. Use concise answers."},
                {"role":"user","content":prompt}]
    result = provider.chat(messages, temperature=0.2, max_tokens=800)
    console.print(Panel(result.get("text",""), title=f"{provider.name} reply"))

def cmd_edit(conf, args):
    if len(args) < 2:
        console.print("Usage: /edit <path> <instruction...>"); return
    path = args[0]; instruction = " ".join(args[1:])
    prof = cfg.active_profile(conf)
    old, err = fileops.read_text(path, prof.get("roots", []))
    if err: console.print(f"[red]{err}[/red]"); return
    provider = make_provider(prof.get("provider"), prof.get("model"))
    messages = [
        {"role":"system","content":SYS_EDIT_PROMPT},
        {"role":"user","content":f"FILEPATH: {path}\n---BEGIN FILE---\n{old}\n---END FILE---\nINSTRUCTION: {instruction}"}
    ]
    res = provider.chat(messages, temperature=0.1, max_tokens=len(old)//2 + 1200)
    new = res.get("text","")
    if not new.strip():
        console.print("[red]Model returned empty content; no changes applied.[/red]"); return
    patch = diffing.unified_diff(old, new, path)
    console.rule(f"Proposed diff for {path}")
    console.print(patch or "(no changes)")
    if not patch.strip():
        return
    if Confirm.ask("Apply this patch?", default=False):
        err2 = fileops.write_text(path, new, prof.get("roots", []))
        if err2: console.print(f"[red]{err2}[/red]"); return
        audit.log("edit-apply", detail=f"applied diff", path=path)
        console.print("[green]Applied.[/green]  Use /commit <msg> to commit.")

def cmd_exec(conf, args):
    if not args:
        console.print("Usage: /exec <command>"); return
    cmd = " ".join(args)
    if not Confirm.ask(f"Run shell command?\n[bold]{cmd}[/bold]", default=False):
        console.print("Aborted."); return
    code, out, err = sh.run(cmd, cwd=os.getcwd())
    console.rule(f"exit={code}")
    if out: console.print(out)
    if err: console.print(f"[red]{err}[/red]")
    audit.log("exec", detail=f"code={code} {cmd}")

def cmd_deps(conf, args):
    det = depdet.detect(".")
    if not det:
        console.print("No dependency files detected."); return
    console.print(Panel("\n".join(f"- {k}: {p}" for k,p in det), title="Detected dependency manifests"))
    cmds = depdet.suggest_commands(det)
    if not cmds:
        console.print("No install commands suggested."); return
    for c in cmds:
        if Confirm.ask(f"Run: {c} ?", default=False):
            code, out, err = sh.run(c, cwd=os.getcwd())
            console.rule(f"{c} -> exit {code}")
            if out: console.print(out)
            if err: console.print(f"[red]{err}[/red]")
            audit.log("deps-run", detail=c)

def repl():
    conf = cfg.load()
    banner(conf)
    while True:
        try:
            s = console.input("[bold cyan]> [/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print(); break
        if not s: continue
        if s in ("/exit","/quit"): break
        if s.startswith("/status"): cmd_status(conf); continue
        if s.startswith("/roots"): cmd_roots(conf, s.split()[1:]); continue
        if s.startswith("/open "): cmd_open(conf, s.split()[1:]); continue
        if s.startswith("/write "): cmd_write(conf, s.split()[1:]); continue
        if s.startswith("/diff "): cmd_diff(conf, s.split()[1:]); continue
        if s.startswith("/commit"): cmd_commit(conf, s.split()[1:]); continue
        if s.startswith("/revert "): cmd_revert(conf, s.split()[1:]); continue
        if s.startswith("/edit "): cmd_edit(conf, s.split()[1:]); continue
        if s.startswith("/exec "): cmd_exec(conf, s.split()[1:]); continue
        if s.startswith("/deps"): cmd_deps(conf, s.split()[1:]); continue
        do_chat(conf, s)

if __name__ == "__main__":
    repl()
