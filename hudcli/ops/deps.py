from __future__ import annotations
from pathlib import Path
from typing import List, Tuple

def detect(base: str = ".") -> List[Tuple[str,str]]:
    """Return list of (kind, path). kind in {'pip','poetry','npm','pnpm','yarn'}"""
    basep = Path(base)
    out = []
    if (basep / "requirements.txt").exists():
        out.append(("pip", str(basep / "requirements.txt")))
    if (basep / "pyproject.toml").exists():
        out.append(("poetry", str(basep / "pyproject.toml")))
    if (basep / "package.json").exists():
        out.append(("npm", str(basep / "package.json")))
    if (basep / "pnpm-lock.yaml").exists():
        out.append(("pnpm", str(basep / "pnpm-lock.yaml")))
    if (basep / "yarn.lock").exists():
        out.append(("yarn", str(basep / "yarn.lock")))
    return out

def suggest_commands(detections: List[Tuple[str,str]]) -> List[str]:
    cmds = []
    kinds = {k for k,_ in detections}
    if "pip" in kinds:
        cmds.append("python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt")
    if "poetry" in kinds:
        cmds.append("poetry install")
    if "npm" in kinds and "pnpm" not in kinds and "yarn" not in kinds:
        cmds.append("npm install")
    if "pnpm" in kinds:
        cmds.append("pnpm install")
    if "yarn" in kinds:
        cmds.append("yarn install")
    return cmds
