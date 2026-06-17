#!/usr/bin/env python3
"""HTDM desktop configurator (Tkinter, couch-friendly navigation)."""

from __future__ import annotations

import argparse
import os
import struct
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from config_store import (
    DEFAULT_CURRENT_THEME_PATH,
    DEFAULT_GUI_STATE_PATH,
    DEFAULT_POLICY_PATH,
    DEFAULT_PRESETS_PATH,
    FALLBACK_GUI_STATE_PATH,
    VALID_AUTO_MODES,
    VALID_RESUME_ACTIONS,
    load_current_theme,
    load_gui_state,
    load_policy,
    load_theme_presets,
    parse_session_pair,
    save_current_theme,
    save_gui_state,
    save_policy,
    validate_env_key,
    validate_path,
    validate_user_csv,
    validate_username,
)


class ControllerReader(threading.Thread):
    """Very small linux joystick reader for basic directional input."""

    EVENT_FORMAT = "IhBB"
    EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

    def __init__(self, app: "ConfiguratorApp", repeat_ms: int = 180) -> None:
        super().__init__(daemon=True)
        self.app = app
        self.repeat_ms = max(80, repeat_ms)
        self.stop_event = threading.Event()
        self.last_emit = 0.0

    def run(self) -> None:
        for device_path in ("/dev/input/js0", "/dev/input/js1"):
            if not Path(device_path).exists():
                continue
            try:
                with open(device_path, "rb", buffering=0) as dev:
                    self._read_loop(dev)
            except OSError:
                continue
            if self.stop_event.is_set():
                break

    def stop(self) -> None:
        self.stop_event.set()

    def _read_loop(self, dev) -> None:
        while not self.stop_event.is_set():
            chunk = dev.read(self.EVENT_SIZE)
            if len(chunk) != self.EVENT_SIZE:
                break
            _, value, event_type, number = struct.unpack(self.EVENT_FORMAT, chunk)
            if event_type & 0x80:
                continue
            if event_type & 0x01:
                self._button_event(number, value)
            elif event_type & 0x02:
                self._axis_event(number, value)

    def _should_emit(self) -> bool:
        now = time.monotonic()
        threshold = self.repeat_ms / 1000.0
        if now - self.last_emit < threshold:
            return False
        self.last_emit = now
        return True

    def _emit(self, action: str) -> None:
        self.app.event_generate(action, when="tail")

    def _button_event(self, number: int, value: int) -> None:
        if value != 1:
            return
        if number == 0:
            self._emit("<<ControllerActivate>>")
        elif number == 1:
            self._emit("<<ControllerBack>>")

    def _axis_event(self, number: int, value: int) -> None:
        if not self._should_emit():
            return
        if number in {0, 6}:
            if value <= -16000:
                self._emit("<<ControllerLeft>>")
            elif value >= 16000:
                self._emit("<<ControllerRight>>")
        elif number in {1, 7}:
            if value <= -16000:
                self._emit("<<ControllerUp>>")
            elif value >= 16000:
                self._emit("<<ControllerDown>>")


class ConfiguratorApp(tk.Tk):
    def __init__(self, policy_path: Path, presets_path: Path, gui_state_path: Path) -> None:
        super().__init__()
        self.title("HTDM Desktop Configurator")
        self.geometry("980x620")
        self.minsize(880, 560)

        self.policy_path = policy_path
        self.policy = load_policy(policy_path)
        self.presets_path = Path(self.policy.get("HTDM_THEME_PRESET_FILE", str(presets_path)))
        self.current_theme_path = Path(
            self.policy.get("HTDM_CURRENT_THEME_FILE", str(DEFAULT_CURRENT_THEME_PATH))
        )
        self.theme_data = load_theme_presets(self.presets_path)
        self.current_theme = load_current_theme(self.current_theme_path)
        self.gui_state_path = gui_state_path
        self.gui_state = load_gui_state(gui_state_path)
        self.controller: ControllerReader | None = None

        self.categories = [
            "Themes",
            "Auto Launch / Sessions",
            "Authentication",
            "Resume & Power",
            "Controllers",
        ]

        self._build_styles()
        self._build_layout()
        self._bind_navigation()
        self._populate_values()
        self._switch_category(0)
        self._maybe_start_controller()

    def _build_styles(self) -> None:
        self.configure(bg="#12151c")
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Root.TFrame", background="#12151c")
        style.configure("Sidebar.TFrame", background="#171b24")
        style.configure("Content.TFrame", background="#12151c")
        style.configure("Header.TLabel", background="#12151c", foreground="#e6ebf5", font=("Sans", 14, "bold"))
        style.configure("Body.TLabel", background="#12151c", foreground="#d2d8e5")

    def _build_layout(self) -> None:
        root = ttk.Frame(self, style="Root.TFrame", padding=14)
        root.pack(fill="both", expand=True)

        self.sidebar = ttk.Frame(root, style="Sidebar.TFrame", padding=10)
        self.sidebar.pack(side="left", fill="y")
        self.content = ttk.Frame(root, style="Content.TFrame", padding=(18, 4))
        self.content.pack(side="right", fill="both", expand=True)

        title = ttk.Label(self.sidebar, text="HTDM Settings", style="Header.TLabel")
        title.pack(anchor="w", pady=(0, 8))
        hint = ttk.Label(self.sidebar, text="D-pad/Arrows: move\nA/Enter: select\nB/Esc: back", style="Body.TLabel")
        hint.pack(anchor="w", pady=(0, 8))

        self.category_list = tk.Listbox(
            self.sidebar,
            activestyle="none",
            height=len(self.categories),
            exportselection=False,
            bg="#1f2430",
            fg="#e5ebf9",
            selectbackground="#3d5d89",
            selectforeground="#ffffff",
            relief="flat",
            highlightthickness=0,
        )
        for cat in self.categories:
            self.category_list.insert("end", cat)
        self.category_list.pack(fill="x")
        self.category_list.bind("<<ListboxSelect>>", self._on_category_select)
        self.category_list.focus_set()

        self.page_title = ttk.Label(self.content, text="", style="Header.TLabel")
        self.page_title.pack(anchor="w", pady=(0, 10))
        self.page_host = ttk.Frame(self.content, style="Content.TFrame")
        self.page_host.pack(fill="both", expand=True)

        action_row = ttk.Frame(self.content, style="Content.TFrame")
        action_row.pack(fill="x", pady=(10, 2))
        ttk.Button(action_row, text="Reload", command=self._reload_all).pack(side="left")
        ttk.Button(action_row, text="Save All", command=self._save_all).pack(side="right")

        self.message_var = tk.StringVar(value="Ready.")
        ttk.Label(self.content, textvariable=self.message_var, style="Body.TLabel").pack(anchor="w", pady=(8, 0))

        self.pages: dict[str, ttk.Frame] = {}
        self._build_themes_page()
        self._build_sessions_page()
        self._build_auth_page()
        self._build_resume_page()
        self._build_controllers_page()

    def _bind_navigation(self) -> None:
        self.bind("<Up>", lambda _: self._nav("up"))
        self.bind("<Down>", lambda _: self._nav("down"))
        self.bind("<Left>", lambda _: self._nav("left"))
        self.bind("<Right>", lambda _: self._nav("right"))
        self.bind("<Return>", lambda _: self._activate_focused())
        self.bind("<Escape>", lambda _: self._back())
        self.bind("<<ControllerUp>>", lambda _: self._nav("up"))
        self.bind("<<ControllerDown>>", lambda _: self._nav("down"))
        self.bind("<<ControllerLeft>>", lambda _: self._nav("left"))
        self.bind("<<ControllerRight>>", lambda _: self._nav("right"))
        self.bind("<<ControllerActivate>>", lambda _: self._activate_focused())
        self.bind("<<ControllerBack>>", lambda _: self._back())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_section(self, title: str) -> ttk.Frame:
        frame = ttk.Frame(self.page_host, style="Content.TFrame")
        self.pages[title] = frame
        return frame

    def _build_themes_page(self) -> None:
        page = self._build_section("Themes")
        ttk.Label(page, text="Preset Theme", style="Body.TLabel").pack(anchor="w")
        self.theme_var = tk.StringVar()
        self.theme_combo = ttk.Combobox(page, state="readonly", textvariable=self.theme_var, width=40)
        self.theme_combo.pack(anchor="w", pady=(4, 8))
        self.theme_combo.bind("<<ComboboxSelected>>", lambda _: self._preview_theme())

        self.theme_preview = tk.Text(page, width=78, height=14, bg="#0f1218", fg="#d6deed")
        self.theme_preview.pack(fill="x", pady=(4, 10))

        row = ttk.Frame(page, style="Content.TFrame")
        row.pack(anchor="w")
        ttk.Button(row, text="Apply Theme", command=self._save_theme).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Reset Recommended", command=self._reset_theme).pack(side="left")

    def _build_sessions_page(self) -> None:
        page = self._build_section("Auto Launch / Sessions")
        self.gaming_user_var = tk.StringVar()
        self.default_desktop_var = tk.StringVar()
        self.auto_launch_mode_var = tk.StringVar()
        self.auto_launch_session_var = tk.StringVar()

        ttk.Label(page, text="Gaming User", style="Body.TLabel").pack(anchor="w")
        ttk.Entry(page, textvariable=self.gaming_user_var, width=30).pack(anchor="w", pady=(3, 8))

        ttk.Label(page, text="Default Desktop Session", style="Body.TLabel").pack(anchor="w")
        self.default_desktop_combo = ttk.Combobox(page, state="readonly", textvariable=self.default_desktop_var, width=30)
        self.default_desktop_combo.pack(anchor="w", pady=(3, 8))

        ttk.Label(page, text="Auto Launch Mode", style="Body.TLabel").pack(anchor="w")
        self.auto_launch_combo = ttk.Combobox(
            page,
            state="readonly",
            textvariable=self.auto_launch_mode_var,
            values=["off", "game", "desktop"],
            width=20,
        )
        self.auto_launch_combo.pack(anchor="w", pady=(3, 8))

        ttk.Label(page, text="Auto Launch Session ID (optional)", style="Body.TLabel").pack(anchor="w")
        ttk.Entry(page, textvariable=self.auto_launch_session_var, width=30).pack(anchor="w", pady=(3, 0))

    def _build_auth_page(self) -> None:
        page = self._build_section("Authentication")
        self.auth_marker_var = tk.StringVar()
        self.allowed_users_var = tk.StringVar()

        ttk.Label(page, text="Desktop Auth Marker Env Var", style="Body.TLabel").pack(anchor="w")
        ttk.Entry(page, textvariable=self.auth_marker_var, width=35).pack(anchor="w", pady=(3, 10))
        ttk.Label(
            page,
            text="Used by launch wrapper to verify desktop auth was completed.",
            style="Body.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        ttk.Label(page, text="Allowed Desktop Users (CSV)", style="Body.TLabel").pack(anchor="w")
        ttk.Entry(page, textvariable=self.allowed_users_var, width=55).pack(anchor="w", pady=(3, 0))

    def _build_resume_page(self) -> None:
        page = self._build_section("Resume & Power")
        self.resume_state_var = tk.StringVar()
        self.resume_action_var = tk.StringVar()
        self.resume_default_var = tk.StringVar()

        ttk.Label(page, text="Resume State File", style="Body.TLabel").pack(anchor="w")
        ttk.Entry(page, textvariable=self.resume_state_var, width=70).pack(anchor="w", pady=(3, 8))

        ttk.Label(page, text="Resume Action File", style="Body.TLabel").pack(anchor="w")
        ttk.Entry(page, textvariable=self.resume_action_var, width=70).pack(anchor="w", pady=(3, 8))

        ttk.Label(page, text="Default Resume Action", style="Body.TLabel").pack(anchor="w")
        self.resume_default_combo = ttk.Combobox(
            page,
            state="readonly",
            textvariable=self.resume_default_var,
            values=["return-to-game", "switch-to-desktop", "sign-out"],
            width=24,
        )
        self.resume_default_combo.pack(anchor="w", pady=(3, 0))

    def _build_controllers_page(self) -> None:
        page = self._build_section("Controllers")
        self.controller_enabled_var = tk.BooleanVar(value=True)
        self.controller_repeat_var = tk.StringVar()

        ttk.Checkbutton(page, text="Enable joystick/controller input", variable=self.controller_enabled_var).pack(
            anchor="w", pady=(0, 10)
        )
        ttk.Label(page, text="Repeat Rate (milliseconds, 80-600)", style="Body.TLabel").pack(anchor="w")
        ttk.Entry(page, textvariable=self.controller_repeat_var, width=16).pack(anchor="w", pady=(3, 10))
        ttk.Label(
            page,
            text="Controller settings are stored in htdm/configurator.json.",
            style="Body.TLabel",
        ).pack(anchor="w")

    def _on_category_select(self, _event) -> None:
        selected = self.category_list.curselection()
        if not selected:
            return
        self._switch_category(selected[0])

    def _switch_category(self, index: int) -> None:
        if index < 0 or index >= len(self.categories):
            return
        self.category_list.selection_clear(0, "end")
        self.category_list.selection_set(index)
        self.category_list.activate(index)
        title = self.categories[index]
        self.page_title.configure(text=title)

        for page in self.pages.values():
            page.pack_forget()
        self.pages[title].pack(fill="both", expand=True)

    def _focus_first_input(self) -> None:
        page = self.pages.get(self.page_title.cget("text"))
        if not page:
            return
        for child in page.winfo_children():
            if isinstance(child, (ttk.Entry, ttk.Combobox, ttk.Checkbutton, ttk.Button, tk.Text)):
                child.focus_set()
                return

    def _nav(self, direction: str) -> None:
        focus = self.focus_get()
        in_sidebar = self._is_descendant(focus, self.sidebar)
        if direction in {"up", "down"} and in_sidebar:
            delta = -1 if direction == "up" else 1
            current = self.category_list.curselection()
            index = current[0] if current else 0
            self._switch_category(max(0, min(len(self.categories) - 1, index + delta)))
            return
        if direction == "right" and in_sidebar:
            self._focus_first_input()
            return
        if direction == "left" and not in_sidebar:
            self.category_list.focus_set()
            return

        if direction == "up":
            nxt = focus.tk_focusPrev() if focus else None
        elif direction == "down":
            nxt = focus.tk_focusNext() if focus else None
        else:
            nxt = None
        if nxt:
            nxt.focus_set()

    def _activate_focused(self) -> None:
        focus = self.focus_get()
        if focus is self.category_list:
            selected = self.category_list.curselection()
            if selected:
                self._switch_category(selected[0])
                self._focus_first_input()
            return
        try:
            focus.invoke()  # ttk.Button/Checkbutton
            return
        except Exception:
            pass
        if isinstance(focus, ttk.Combobox):
            return
        if isinstance(focus, tk.Text):
            return
        self._save_all()

    def _back(self) -> None:
        focus = self.focus_get()
        if self._is_descendant(focus, self.sidebar):
            self._on_close()
        else:
            self.category_list.focus_set()

    @staticmethod
    def _is_descendant(widget, parent) -> bool:
        if widget is None:
            return False
        current = widget
        while current is not None:
            if current == parent:
                return True
            current = current.master
        return False

    def _get_session_ids(self, keys: list[str]) -> list[str]:
        values: list[str] = []
        for key in keys:
            parsed = parse_session_pair(self.policy.get(key, ""))
            if parsed:
                values.append(parsed[0])
        return values

    def _populate_values(self) -> None:
        presets = self.theme_data.get("presets", [])
        theme_ids = [preset.get("id", "") for preset in presets if preset.get("id")]
        self.theme_combo.configure(values=theme_ids)
        active_theme = self.current_theme.get("active_preset") or self.theme_data.get("recommended", "")
        self.theme_var.set(active_theme if active_theme in theme_ids else (theme_ids[0] if theme_ids else ""))
        self._preview_theme()

        desktop_ids = self._get_session_ids(["HTDM_DESKTOP_SESSION_GNOME", "HTDM_DESKTOP_SESSION_KDE"])
        if not desktop_ids:
            desktop_ids = ["gnome", "kde"]
        self.default_desktop_combo.configure(values=desktop_ids)
        default_desktop = self.policy.get("HTDM_DEFAULT_DESKTOP_SESSION", desktop_ids[0])
        self.default_desktop_var.set(default_desktop if default_desktop in desktop_ids else desktop_ids[0])

        self.gaming_user_var.set(self.policy.get("HTDM_GAMING_USER", "gaming"))
        self.auto_launch_mode_var.set(self.policy.get("HTDM_AUTO_LAUNCH_MODE", "off"))
        self.auto_launch_session_var.set(self.policy.get("HTDM_AUTO_LAUNCH_SESSION", ""))
        self.auth_marker_var.set(self.policy.get("HTDM_AUTH_MARKER_ENV", "HTDM_DESKTOP_AUTH_OK"))
        self.allowed_users_var.set(self.policy.get("HTDM_ALLOWED_DESKTOP_USERS", ""))

        self.resume_state_var.set(self.policy.get("HTDM_RESUME_STATE_FILE", "/run/htdm/resume/state.env"))
        self.resume_action_var.set(self.policy.get("HTDM_RESUME_ACTION_FILE", "/run/htdm/resume/action"))
        self.resume_default_var.set(self.policy.get("HTDM_RESUME_DEFAULT_ACTION", "return-to-game"))

        self.controller_enabled_var.set(bool(self.gui_state.get("controller_enabled", True)))
        self.controller_repeat_var.set(str(int(self.gui_state.get("controller_repeat_ms", 180))))

    def _preview_theme(self) -> None:
        selected = self.theme_var.get().strip()
        presets = self.theme_data.get("presets", [])
        match = next((preset for preset in presets if preset.get("id") == selected), None)
        if not match:
            self.theme_preview.delete("1.0", "end")
            self.theme_preview.insert("1.0", "No preset selected.")
            return
        lines = [f"{match.get('name', selected)} ({selected})", ""]
        for token_name, token_value in match.get("tokens", {}).items():
            lines.append(f"{token_name}: {token_value}")
        self.theme_preview.delete("1.0", "end")
        self.theme_preview.insert("1.0", "\n".join(lines))

    def _reset_theme(self) -> None:
        rec = self.theme_data.get("recommended", "")
        values = list(self.theme_combo.cget("values"))
        if rec in values:
            self.theme_var.set(rec)
            self._preview_theme()

    def _validate_all(self) -> list[str]:
        errors: list[str] = []
        if not validate_username(self.gaming_user_var.get().strip()):
            errors.append("Gaming user must match Linux username rules.")
        if self.auto_launch_mode_var.get().strip() not in VALID_AUTO_MODES:
            errors.append("Auto launch mode must be off, game, or desktop.")
        if not validate_env_key(self.auth_marker_var.get().strip()):
            errors.append("Auth marker must be an uppercase env variable name.")
        if not validate_user_csv(self.allowed_users_var.get().strip()):
            errors.append("Allowed desktop users must be a comma-separated username list.")
        if not validate_path(self.resume_state_var.get().strip()):
            errors.append("Resume state file path must be absolute.")
        if not validate_path(self.resume_action_var.get().strip()):
            errors.append("Resume action file path must be absolute.")
        if self.resume_default_var.get().strip() not in VALID_RESUME_ACTIONS:
            errors.append("Default resume action must be return-to-game, switch-to-desktop, or sign-out.")
        try:
            repeat_ms = int(self.controller_repeat_var.get().strip())
            if repeat_ms < 80 or repeat_ms > 600:
                raise ValueError
        except ValueError:
            errors.append("Controller repeat rate must be a number from 80 to 600.")
        return errors

    def _save_theme(self) -> None:
        selected = self.theme_var.get().strip()
        preset = next((item for item in self.theme_data.get("presets", []) if item.get("id") == selected), None)
        if not preset:
            messagebox.showerror("Theme", "Selected theme preset does not exist.")
            return
        try:
            written = save_current_theme(self.current_theme_path, selected, preset.get("tokens", {}))
        except OSError as exc:
            messagebox.showerror("Theme", f"Failed to save current theme: {exc}")
            return
        self.message_var.set(f"Theme saved to {written}")

    def _save_all(self) -> None:
        errors = self._validate_all()
        if errors:
            messagebox.showerror("Validation", "\n".join(f"- {item}" for item in errors))
            return

        policy_updates = self.policy.copy()
        policy_updates["HTDM_GAMING_USER"] = self.gaming_user_var.get().strip()
        policy_updates["HTDM_DEFAULT_DESKTOP_SESSION"] = self.default_desktop_var.get().strip()
        policy_updates["HTDM_AUTO_LAUNCH_MODE"] = self.auto_launch_mode_var.get().strip()
        policy_updates["HTDM_AUTO_LAUNCH_SESSION"] = self.auto_launch_session_var.get().strip()
        policy_updates["HTDM_AUTH_MARKER_ENV"] = self.auth_marker_var.get().strip()
        policy_updates["HTDM_ALLOWED_DESKTOP_USERS"] = self.allowed_users_var.get().strip()
        policy_updates["HTDM_RESUME_STATE_FILE"] = self.resume_state_var.get().strip()
        policy_updates["HTDM_RESUME_ACTION_FILE"] = self.resume_action_var.get().strip()
        policy_updates["HTDM_RESUME_DEFAULT_ACTION"] = self.resume_default_var.get().strip()

        try:
            saved_policy_path = save_policy(self.policy_path, policy_updates)
            self.policy = load_policy(saved_policy_path)
        except OSError as exc:
            messagebox.showerror("Save", f"Failed to write policy env: {exc}")
            return

        gui_state = {
            "controller_enabled": bool(self.controller_enabled_var.get()),
            "controller_repeat_ms": int(self.controller_repeat_var.get().strip()),
        }
        try:
            saved_gui_path = save_gui_state(self.gui_state_path, gui_state)
            self.gui_state = gui_state
        except OSError as exc:
            messagebox.showerror("Save", f"Failed to write controller settings: {exc}")
            return

        self._save_theme()
        self._restart_controller()
        self.message_var.set(f"Saved policy {saved_policy_path} and controller settings {saved_gui_path}")

    def _reload_all(self) -> None:
        self.policy = load_policy(self.policy_path)
        self.presets_path = Path(self.policy.get("HTDM_THEME_PRESET_FILE", str(DEFAULT_PRESETS_PATH)))
        self.current_theme_path = Path(
            self.policy.get("HTDM_CURRENT_THEME_FILE", str(DEFAULT_CURRENT_THEME_PATH))
        )
        self.theme_data = load_theme_presets(self.presets_path)
        self.current_theme = load_current_theme(self.current_theme_path)
        self.gui_state = load_gui_state(self.gui_state_path)
        self._populate_values()
        self._restart_controller()
        self.message_var.set("Reloaded from config files.")

    def _maybe_start_controller(self) -> None:
        if not bool(self.gui_state.get("controller_enabled", True)):
            return
        repeat_ms = int(self.gui_state.get("controller_repeat_ms", 180))
        self.controller = ControllerReader(self, repeat_ms=repeat_ms)
        self.controller.start()

    def _restart_controller(self) -> None:
        if self.controller:
            self.controller.stop()
            self.controller = None
        if self.controller_enabled_var.get():
            try:
                repeat_ms = int(self.controller_repeat_var.get().strip())
            except ValueError:
                repeat_ms = 180
            self.controller = ControllerReader(self, repeat_ms=repeat_ms)
            self.controller.start()

    def _on_close(self) -> None:
        if self.controller:
            self.controller.stop()
        self.destroy()


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    policy = Path(args.policy_file or os.environ.get("HTDM_POLICY_FILE", str(DEFAULT_POLICY_PATH)))
    presets = Path(args.theme_presets or os.environ.get("HTDM_THEME_PRESET_FILE", str(DEFAULT_PRESETS_PATH)))
    gui_state = Path(args.gui_state_file or os.environ.get("HTDM_CONFIGURATOR_FILE", str(DEFAULT_GUI_STATE_PATH)))
    return policy, presets, gui_state


def main() -> int:
    parser = argparse.ArgumentParser(description="HTDM desktop settings configurator")
    parser.add_argument("--policy-file", help="Path to session-policy env file")
    parser.add_argument("--theme-presets", help="Path to theme presets json")
    parser.add_argument("--gui-state-file", help="Path to configurator state json")
    args = parser.parse_args()

    policy_path, presets_path, gui_state_path = resolve_paths(args)
    try:
        app = ConfiguratorApp(policy_path=policy_path, presets_path=presets_path, gui_state_path=gui_state_path)
    except OSError:
        app = ConfiguratorApp(
            policy_path=policy_path,
            presets_path=presets_path,
            gui_state_path=FALLBACK_GUI_STATE_PATH,
        )
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
