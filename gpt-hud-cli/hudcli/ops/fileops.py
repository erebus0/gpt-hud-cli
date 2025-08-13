from __future__ import annotations
from pathlib import Path
from typing import Iterable, List, Tuple

def normalize(p: str) -> str:
    return str(Path(p).expanduser().resolve())

def is_in_roots(path: str, roots: Iterable[str]) -> bool:
    P = Path(normalize(path))
    for r in roots:
        try:
            if P.is_relative_to(r):
                return True
        except AttributeError:
            # Python <3.9 fallback
            if str(P).startswith(str(normalize(r))):
                return True
    return False

def read_text(path: str, roots: Iterable[str], max_bytes: int = 1024*1024) -> Tuple[str, str]:
    p = Path(normalize(path))
    if not is_in_roots(p, roots):
        return "", f"Path {p} is outside allowed roots"
    if not p.exists():
        return "", f"File not found: {p}"
    b = p.read_bytes()
    if len(b) > max_bytes:
        return "", f"File too large: {len(b)} bytes > {max_bytes}"
    try:
        return b.decode("utf-8", errors="ignore"), ""
    except Exception as e:
        return "", f"Decode error: {e}"

def write_text(path: str, content: str, roots: Iterable[str]) -> str:
    p = Path(normalize(path))
    if not is_in_roots(p, roots):
        return f"Path {p} is outside allowed roots"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return ""
