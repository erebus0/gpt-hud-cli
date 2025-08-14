from __future__ import annotations
import os, shutil
from pathlib import Path
import yaml

NEW_HOME_ENV = "HUD_HOME"
LEGACY_HOME_ENV = "GPT_HUD_HOME"

def _resolve_app_dir() -> Path:
    home = os.environ.get(NEW_HOME_ENV) or os.environ.get(LEGACY_HOME_ENV)
    if home:
        return Path(home).expanduser()
    new_dir = Path.home() / ".hud_cli"
    legacy_dir = Path.home() / ".gpt_hud"
    if legacy_dir.exists() and not new_dir.exists():
        try:
            new_dir.mkdir(parents=True, exist_ok=True)
            for name in ("config.yaml", "audit.log"):
                src = legacy_dir / name
                if src.exists():
                    (new_dir / name).write_bytes(src.read_bytes())
        except Exception:
            pass
    return new_dir

APP_DIR = _resolve_app_dir()
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
