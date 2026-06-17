# HTDM Desktop Configurator

The desktop configurator provides a couch-friendly settings UI for core HTDM policy
values and theme selection.

## Launch

- Repository/dev launch:
  - `python3 scripts/configurator/htdm_configurator.py`
- Optional overrides:
  - `--policy-file /etc/htdm/session-policy.env`
  - `--theme-presets /etc/htdm/themes/presets.json`
  - `--gui-state-file /etc/htdm/configurator.json`

If `/etc/htdm/configurator.json` is not writable, the app falls back to
`~/.config/htdm/configurator.json`.

## Navigation

- Keyboard: arrows move focus, `Enter` activates, `Esc` goes back.
- Controller (basic): D-pad or left stick move focus, button `A` activates,
  button `B` goes back.
- Sidebar categories:
  - `Themes`
  - `Auto Launch / Sessions`
  - `Authentication`
  - `Resume & Power`
  - `Controllers`

## Persistence Mapping

### Existing HTDM policy file

Most controls save to `session-policy.env` (default `/etc/htdm/session-policy.env`):

- `HTDM_GAMING_USER`
- `HTDM_AUTH_MARKER_ENV`
- `HTDM_ALLOWED_DESKTOP_USERS`
- `HTDM_RESUME_STATE_FILE`
- `HTDM_RESUME_ACTION_FILE`
- `HTDM_AUTO_LAUNCH_MODE` (`off|game|desktop`)
- `HTDM_AUTO_LAUNCH_SESSION`
- `HTDM_DEFAULT_DESKTOP_SESSION`
- `HTDM_RESUME_DEFAULT_ACTION` (`return-to-game|switch-to-desktop|sign-out`)

Unknown keys are preserved when saving.

### Existing HTDM theme files

- Presets source: `HTDM_THEME_PRESET_FILE` (default `/etc/htdm/themes/presets.json`)
- Active theme output: `HTDM_CURRENT_THEME_FILE`
  (default `/var/lib/htdm/theme/current-theme.json`)

The active theme payload keeps the existing shape:

- `active_preset`
- `tokens`

### New minimal file

`/etc/htdm/configurator.json` stores configurator-local controller preferences:

- `controller_enabled` (bool)
- `controller_repeat_ms` (80-600)

This file is intentionally small and isolated from launch/auth policy.

## Validation and Defaults

The app applies safe defaults when files are missing and validates before write:

- Linux username format for `HTDM_GAMING_USER` and desktop allow-list CSV items
- Uppercase environment variable format for `HTDM_AUTH_MARKER_ENV`
- Absolute paths for resume files
- Enum checks for auto launch mode and resume action
- Numeric range check for controller repeat rate

Validation failures are shown in a modal and no files are changed.
