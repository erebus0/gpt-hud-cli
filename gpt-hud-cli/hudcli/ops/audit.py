from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional
from .. import config as cfg

def log(event: str, detail: str = "", path: Optional[str] = None) -> None:
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    line = f"{ts}\t{event}\t{path or ''}\t{detail}\n"
    with open(cfg.AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(line)
