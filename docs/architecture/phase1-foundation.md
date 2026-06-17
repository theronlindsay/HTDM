# Phase 1 Foundation: Controller-First Execution Stream

## Decision: Base Stack

HTDM chooses a **greetd-first** architecture for the controller-first experience.

Rationale:
- `greetd` is minimal and PAM-aware.
- Session launch policy can be enforced by external wrappers.
- It avoids maintaining a deep fork of `gdm` or `sddm`.

## Session Boundary Model

Phase 1 defines two explicit trust boundaries:

1. **Unauthenticated game path**
   - Runs as a constrained `gaming` account.
   - Does not run desktop session wrappers.
   - Uses a dedicated non-auth PAM service (`htdm-game-open`) for account/session setup only.
   - Any optional PIN in game mode is app-level UX, not system auth.

2. **Authenticated desktop path**
   - Launches GNOME/KDE only after successful PAM auth.
   - Uses a dedicated auth PAM service (`htdm-desktop-auth`).
   - Wrapper scripts fail closed if auth tokens/environment are not present.

## Launcher Wrapper Responsibilities

- `launch-game.sh`
  - Validates target user is the configured gaming user.
  - Allows only game session commands.
  - Exits on unknown session names.

- `launch-desktop.sh`
  - Requires explicit authenticated marker from the greeter/controller.
  - Allows only approved desktop sessions.
  - Exits if marker, user allow-list, or session mapping is missing.

- `launch-session.sh`
  - Routes greeter actions to `game` or `desktop` launchers.
  - Fails closed on unknown mode or missing desktop session ID.

## Controller-First Greeter Prototype (MVP)

- `scripts/greeter/controller_greeter_mvp.py` implements a basic 10-foot menu:
  - `Game Mode`, `Desktop (GNOME)`, `Desktop (KDE)`.
  - `Appearance` submenu for curated token presets.
  - Post-resume quick actions:
    - `Return To Game`
    - `Switch To Desktop`
    - `Sign Out And Choose Session`
- It defaults to dry-run launch requests unless `HTDM_GREETER_EXEC=1`.

## Theme System (Curated Token Presets)

- `config/themes/presets.json` provides constrained preset families:
  - `Modern Neutral` (recommended)
  - `KDE-Inspired`
  - `GNOME-Inspired`
  - `Steam-Inspired`
  - `High Contrast`
- Active selection is persisted to `HTDM_CURRENT_THEME_FILE` for machine-level defaults.

## Shared Steam Storage

- `scripts/storage/setup-shared-steam.sh` provisions:
  - Shared root (default `/var/lib/steam-shared`),
  - `steamlib` group with `gaming` and optional desktop users,
  - setgid directories and default ACLs (`rwx`) for safe mixed writes.
- `scripts/storage/check-shared-steam-health.sh` validates:
  - Group ownership, setgid bit, ACL defaults, and user membership.

## Suspend/Hibernate Resume Flow

- `config/systemd/system-sleep/htdm-sleep-hook` + `scripts/power/htdm-sleep-hook.sh`
  capture pre/post suspend and hibernate transitions into resume state.
- `config/systemd/htdm-resume-handler.service` + `scripts/power/htdm-resume-handler.sh`
  process post-resume quick actions and route to game or desktop launcher.
- Session wrappers clear stale action files after successful launch.

## File Layout

- `config/greetd/config.toml.example`
  - greetd scaffold with explicit session commands and placeholders.
- `config/pam/htdm-desktop-auth`
  - Desktop PAM service with `system-auth`/`password-auth` include flow.
- `config/pam/htdm-game-open`
  - Non-auth game PAM service for account/session only.
- `config/policy/session-policy.env.example`
  - Environment defaults consumed by wrappers/greeter/resume services.
- `scripts/session/common-policy.sh`
  - Shared allow-list/session resolution and policy helpers.
- `scripts/session/launch-game.sh`
  - Unauthenticated game wrapper.
- `scripts/session/launch-desktop.sh`
  - Authenticated desktop wrapper.
- `scripts/session/launch-session.sh`
  - Mode router wrapper for greeter calls.
- `scripts/greeter/controller_greeter_mvp.py`
  - Controller-first prototype menu and appearance UX.
- `config/themes/presets.json`
  - Curated theme token presets.
- `scripts/storage/setup-shared-steam.sh`
  - Shared Steam directory/group/ACL provisioner.
- `scripts/storage/check-shared-steam-health.sh`
  - Shared Steam health validator.
- `scripts/power/htdm-sleep-hook.sh`
  - Sleep transition state writer.
- `scripts/power/htdm-resume-handler.sh`
  - Resume action dispatcher.
- `config/systemd/htdm-resume-handler.service`
  - Resume oneshot service example.
- `config/systemd/system-sleep/htdm-sleep-hook`
  - systemd sleep hook entrypoint.

## Security Notes for Next Iteration

- Greeter/controller must set an authenticated marker only after PAM success.
- Marker transport should move from plain env var to a tighter mechanism
  (e.g., FD/credential handoff, signed token, or isolated IPC contract).
- Policy marker transport should move to signed/isolated mechanism.
- Steam provisioning scripts require root; package/install tooling must enforce this.
- Resume handler currently trusts action file ownership/path and should harden with strict
  ownership and mount constraints in packaging.

## Remaining Out of Scope

- Full graphics/UI implementation in Wayland compositor.
- Broad matrix validation across GPUs/controllers/distros.
- Immutable and mutable package publish/release automation.
