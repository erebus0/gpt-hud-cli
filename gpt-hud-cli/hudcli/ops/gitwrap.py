from __future__ import annotations
import subprocess, os
from pathlib import Path
from typing import Tuple

def _run(cmd, cwd=None) -> Tuple[int,str,str]:
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    return p.returncode, out, err

def is_repo(cwd=None) -> bool:
    code, out, _ = _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=cwd)
    return code == 0 and out.strip() == "true"

def status(cwd=None) -> str:
    code, out, err = _run(["git", "status", "--short"], cwd=cwd)
    return out if code==0 else err

def diff(path: str, cwd=None) -> str:
    code, out, err = _run(["git", "diff", "--", path], cwd=cwd)
    return out if code==0 else err

def add_all(cwd=None) -> str:
    code, out, err = _run(["git", "add", "-A"], cwd=cwd)
    return out if code==0 else err

def commit(msg: str, cwd=None) -> str:
    code, out, err = _run(["git", "commit", "-m", msg], cwd=cwd)
    return out if code==0 else err

def revert(path: str, cwd=None) -> str:
    code, out, err = _run(["git", "checkout", "--", path], cwd=cwd)
    return out if code==0 else err
