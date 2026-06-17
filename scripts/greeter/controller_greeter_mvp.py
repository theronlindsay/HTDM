#!/usr/bin/env python3
"""Controller-first greeter prototype with appearance menu and resume actions."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


POLICY_FILE = Path(os.environ.get("HTDM_POLICY_FILE", "/etc/htdm/session-policy.env"))
THEME_PRESETS_FILE = Path(os.environ.get("HTDM_THEME_PRESET_FILE", "/etc/htdm/themes/presets.json"))
CURRENT_THEME_FILE = Path(os.environ.get("HTDM_CURRENT_THEME_FILE", "/var/lib/htdm/theme/current-theme.json"))
RESUME_STATE_FILE = Path(os.environ.get("HTDM_RESUME_STATE_FILE", "/run/htdm/resume/state.env"))
RESUME_ACTION_FILE = Path(os.environ.get("HTDM_RESUME_ACTION_FILE", "/run/htdm/resume/action"))
EXEC_ENABLED = os.environ.get("HTDM_GREETER_EXEC", "0") == "1"
LAUNCHER = os.environ.get("HTDM_LAUNCHER", "/usr/local/lib/htdm/session/launch-session.sh")


def parse_env_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        result[key.strip()] = value.strip().strip('"')
    return result


def write_text_with_fallback(path: Path, text: str, fallback: Path) -> Path:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path
    except OSError:
        fallback.parent.mkdir(parents=True, exist_ok=True)
        fallback.write_text(text, encoding="utf-8")
        return fallback


def load_theme_presets(path: Path) -> dict:
    if not path.exists():
        return {"recommended": "modern-neutral", "presets": []}
    return json.loads(path.read_text(encoding="utf-8"))


def launch(mode: str, session: str | None = None) -> None:
    command = [LAUNCHER, mode]
    if session:
        command.append(session)

    print(f"\nLaunch request: {' '.join(command)}")
    if not EXEC_ENABLED:
        print("HTDM_GREETER_EXEC != 1, dry-run only.")
        return

    subprocess.run(command, check=True)


def choose_option(title: str, options: list[str]) -> int:
    print(f"\n== {title} ==")
    for idx, opt in enumerate(options, 1):
        print(f" {idx}. {opt}")
    while True:
        selected = input("> ").strip().lower()
        if selected in {"b", "back"}:
            return -1
        if selected.isdigit():
            index = int(selected) - 1
            if 0 <= index < len(options):
                return index
        print("Use number to select, or 'b' to go back.")


def show_resume_actions() -> None:
    if not RESUME_STATE_FILE.exists():
        return

    state = parse_env_file(RESUME_STATE_FILE)
    if state.get("HTDM_RESUMED", "") != "1":
        return

    print("\nResume detected. Quick actions:")
    options = ["Return To Game", "Switch To Desktop", "Sign Out And Choose Session"]
    selected = choose_option("Post-Resume Actions", options)
    if selected == 0:
        write_text_with_fallback(RESUME_ACTION_FILE, "return-to-game\n", Path("/tmp/htdm-resume-action"))
        launch("game", "gamescope")
    elif selected == 1:
        write_text_with_fallback(RESUME_ACTION_FILE, "switch-to-desktop\n", Path("/tmp/htdm-resume-action"))
        print("Choose desktop target from main menu.")
    elif selected == 2:
        write_text_with_fallback(RESUME_ACTION_FILE, "sign-out\n", Path("/tmp/htdm-resume-action"))
        print("Returning to session menu.")


def appearance_menu(theme_data: dict) -> None:
    presets = theme_data.get("presets", [])
    recommended = theme_data.get("recommended", "")
    if not presets:
        print("No theme presets configured.")
        return

    display = [f"{item['name']} ({item['id']})" for item in presets]
    display.append("Reset To Recommended")
    selected = choose_option("Appearance", display)
    if selected < 0:
        return

    if selected == len(display) - 1:
        chosen = next((p for p in presets if p.get("id") == recommended), presets[0])
    else:
        chosen = presets[selected]

    output = json.dumps({"active_preset": chosen.get("id"), "tokens": chosen.get("tokens", {})}, indent=2)
    saved_path = write_text_with_fallback(CURRENT_THEME_FILE, output + "\n", Path("/tmp/htdm-current-theme.json"))
    print(f"Applied theme: {chosen.get('name')} -> {saved_path}")


def main() -> int:
    policy = parse_env_file(POLICY_FILE)
    theme_data = load_theme_presets(THEME_PRESETS_FILE)

    print("HTDM Controller-First Greeter MVP")
    print("Controller mapping: D-pad ~= number selection, A=enter, B=back (use numbers + b in MVP).")
    if policy.get("HTDM_GAMING_USER"):
        print(f"Configured gaming user: {policy['HTDM_GAMING_USER']}")

    show_resume_actions()

    main_options = [
        "Game Mode",
        "Desktop (GNOME)",
        "Desktop (KDE)",
        "Appearance",
        "Power: Suspend",
        "Power: Hibernate",
        "Exit",
    ]

    while True:
        selected = choose_option("Main Menu", main_options)
        if selected == 0:
            launch("game", "gamescope")
        elif selected == 1:
            launch("desktop", "gnome")
        elif selected == 2:
            launch("desktop", "kde")
        elif selected == 3:
            appearance_menu(theme_data)
        elif selected == 4:
            print("Suspend requested (wire to systemctl suspend in deployed greeter service).")
        elif selected == 5:
            print("Hibernate requested (wire to systemctl hibernate in deployed greeter service).")
        else:
            break

    print("Greeter exited.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
