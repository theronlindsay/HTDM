#!/usr/bin/env python3
"""Config load/save helpers for the HTDM desktop configurator."""

from __future__ import annotations

import json
import re
from pathlib import Path


DEFAULT_POLICY_PATH = Path("/etc/htdm/session-policy.env")
DEFAULT_PRESETS_PATH = Path("/etc/htdm/themes/presets.json")
DEFAULT_CURRENT_THEME_PATH = Path("/var/lib/htdm/theme/current-theme.json")
DEFAULT_GUI_STATE_PATH = Path("/etc/htdm/configurator.json")
FALLBACK_GUI_STATE_PATH = Path.home() / ".config/htdm/configurator.json"

SAFE_POLICY_DEFAULTS: dict[str, str] = {
    "HTDM_GAMING_USER": "gaming",
    "HTDM_AUTH_MARKER_ENV": "HTDM_DESKTOP_AUTH_OK",
    "HTDM_DESKTOP_SESSION_GNOME": "gnome:gnome-session",
    "HTDM_DESKTOP_SESSION_KDE": "kde:startplasma-wayland",
    "HTDM_ALLOWED_DESKTOP_USERS": "",
    "HTDM_GAME_SESSION": "gamescope:gamescope-session",
    "HTDM_THEME_PRESET_FILE": str(DEFAULT_PRESETS_PATH),
    "HTDM_CURRENT_THEME_FILE": str(DEFAULT_CURRENT_THEME_PATH),
    "HTDM_RESUME_STATE_FILE": "/run/htdm/resume/state.env",
    "HTDM_RESUME_ACTION_FILE": "/run/htdm/resume/action",
    "HTDM_AUTO_LAUNCH_MODE": "off",
    "HTDM_AUTO_LAUNCH_SESSION": "",
    "HTDM_DEFAULT_DESKTOP_SESSION": "gnome",
    "HTDM_RESUME_DEFAULT_ACTION": "return-to-game",
}

VALID_AUTO_MODES = {"off", "game", "desktop"}
VALID_RESUME_ACTIONS = {"return-to-game", "switch-to-desktop", "sign-out"}
USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
ENV_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")


def parse_env_text(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        parsed[key.strip()] = value.strip().strip('"')
    return parsed


def load_policy(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return SAFE_POLICY_DEFAULTS.copy()
    loaded = SAFE_POLICY_DEFAULTS.copy()
    loaded.update(parse_env_text(text))
    return loaded


def _format_env_line(key: str, value: str) -> str:
    return f"{key}={value}"


def save_policy(path: Path, updates: dict[str, str]) -> Path:
    merged = SAFE_POLICY_DEFAULTS.copy()
    merged.update(updates)

    try:
        original = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        original = ["# Managed by HTDM desktop configurator.", ""]

    seen: set[str] = set()
    output: list[str] = []
    for line in original:
        if "=" not in line or line.lstrip().startswith("#"):
            output.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in merged:
            output.append(_format_env_line(key, merged[key]))
            seen.add(key)
        else:
            output.append(line)

    missing_keys = [key for key in merged if key not in seen]
    if missing_keys and output and output[-1].strip():
        output.append("")
    for key in missing_keys:
        output.append(_format_env_line(key, merged[key]))

    text = "\n".join(output).rstrip() + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def load_theme_presets(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"recommended": "modern-neutral", "presets": []}


def load_current_theme(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_current_theme(path: Path, active_preset: str, tokens: dict) -> Path:
    payload = {"active_preset": active_preset, "tokens": tokens}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def load_gui_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"controller_enabled": True, "controller_repeat_ms": 180}


def save_gui_state(path: Path, state: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return path


def validate_username(name: str) -> bool:
    return bool(USERNAME_RE.fullmatch(name))


def validate_user_csv(csv_text: str) -> bool:
    if not csv_text.strip():
        return True
    names = [part.strip() for part in csv_text.split(",")]
    return all(validate_username(name) for name in names if name)


def validate_env_key(key: str) -> bool:
    return bool(ENV_KEY_RE.fullmatch(key))


def validate_path(path_text: str) -> bool:
    return path_text.startswith("/")


def parse_session_pair(pair: str) -> tuple[str, str] | None:
    if ":" not in pair:
        return None
    session_id, command = pair.split(":", 1)
    session_id = session_id.strip()
    command = command.strip()
    if not session_id or not command:
        return None
    return session_id, command
