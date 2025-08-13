from __future__ import annotations
import os, yaml
from pathlib import Path

APP_DIR = Path(os.environ.get("GPT_HUD_HOME", Path.home() / ".gpt_hud"))
APP_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = APP_DIR / "config.yaml"
AUDIT_LOG = APP_DIR / "audit.log"

DEFAULTS = {
    "profiles": {
        "default": {
            "provider": os.environ.get("HUD_PROVIDER", "openai"),
            "model": os.environ.get("HUD_MODEL", "gpt-4o-mini"),
            "roots": [],
        }
    },
    "active_profile": "default",
}

def load() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    res = {**DEFAULTS, **data}
    if "profiles" not in res or not isinstance(res["profiles"], dict):
        res["profiles"] = DEFAULTS["profiles"]
    if "active_profile" not in res:
        res["active_profile"] = "default"
    return res

def save(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=True)

def active_profile(cfg: dict) -> dict:
    name = cfg.get("active_profile", "default")
    return cfg["profiles"].setdefault(name, dict(DEFAULTS["profiles"]["default"]))

def set_active_profile(cfg: dict, name: str) -> None:
    cfg["active_profile"] = name
    cfg["profiles"].setdefault(name, dict(DEFAULTS["profiles"]["default"]))

def ensure_root(cfg: dict, path: str) -> None:
    prof = active_profile(cfg)
    roots = prof.setdefault("roots", [])
    p = str(Path(path).resolve())
    if p not in roots:
        roots.append(p)
