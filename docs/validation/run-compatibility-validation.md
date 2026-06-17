# Compatibility Validation Report (`run-compatibility-validation`)

Date: 2026-06-17  
Repository: `HTDM`  
Scope: Phase 1 foundation artifacts and plan-aligned compatibility surfaces

## Validation Matrix (Plan-Aligned)

| Area | Matrix slice | In-repo automated here | Manual/hardware required |
| --- | --- | --- | --- |
| Distros | Fedora/RHEL, Debian/Ubuntu, Arch, rpm-ostree, BlueBuild | Distro routing dry-run on this host | Native package install/upgrade/rollback per distro |
| GPU/graphics | AMD, NVIDIA, Intel (Wayland/gamescope interaction) | Wrapper/policy and greeter dry-runs only | Real compositor + GPU driver validation |
| Controllers | Xbox, DualSense, Switch Pro, generic pads; reconnect | Greeter interaction simulation via stdin only | Physical USB/BT hotplug and focus recovery |
| Suspend/resume | pre/post sleep hook, resume action routing | Hook + resume action file simulation | Real suspend/hibernate wake and UX timing |
| Auth policy | game unauthenticated vs desktop authenticated | Positive/negative wrapper behavior checks | PAM integration end-to-end under greetd |
| Shared Steam storage | group/setgid/default ACL policy | Script syntax and static behavior review | Rooted setup + dual-user write checks |
| Theme behavior | preset load/apply/reset and persistence | Greeter apply + persisted theme file check | 10-foot readability and contrast perception checks |

## What Was Validated Here (Passed)

1. Script and code syntax:
   - `bash -n` passed for all `scripts/session`, `scripts/storage`, `scripts/power`, `scripts/install`.
   - `python3 -m py_compile` passed for `scripts/greeter/controller_greeter_mvp.py`.
2. Session policy behavior:
   - `launch-session.sh` rejects unsupported mode and desktop-without-session.
   - `launch-desktop.sh` rejects missing auth marker and allows known session when marker is present.
   - `launch-game.sh` allows known game session when run with matching `HTDM_GAMING_USER`.
3. Resume flow simulation:
   - `htdm-sleep-hook.sh` writes `HTDM_RESUMED=0` on pre-suspend and `HTDM_RESUMED=1` on post-suspend.
   - `htdm-resume-handler.sh` dispatches `return-to-game` to launcher with `game gamescope`.
4. Greeter/theme behavior:
   - Greeter runs in dry-run mode and exits cleanly.
   - Theme selection writes an `active_preset` payload to the configured current-theme file.
5. Packaging/scaffold sanity:
   - Debian maintainer scripts/rules syntax check passed.
   - Immutable layering helper script syntax check passed.
   - `rpmspec` tool unavailable in this environment (parse check skipped).

## Small Fix Applied During Validation

- File changed: `scripts/install/bootstrap.sh`
- Change: prefer `rpm-ostree` path only when `rpm-ostree status` succeeds.
- Reason: on non-ostree systems where `rpm-ostree` binary is present but unusable, bootstrap now correctly falls back to `dnf`/`yum`.

## Pending Validations (Privileged/System/Hardware)

### 1) Distro + Packaging Matrix

Run on each target OS image:

- Fedora mutable:
  - `sudo ./scripts/install/bootstrap.sh --dry-run`
  - `sudo ./scripts/install/bootstrap.sh`
  - Expected pass: installs via `dnf`/`yum`, defaults applied, no rpm-ostree error path.
- Debian/Ubuntu:
  - `sudo ./scripts/install/bootstrap.sh --dry-run`
  - Expected pass: emits `apt-get` flow.
- Arch:
  - `sudo ./scripts/install/bootstrap.sh --dry-run`
  - Expected pass: emits `pacman` flow.
- Fedora Atomic/Kinoite/Bazzite:
  - `sudo ./packaging/immutable/rpm-ostree/layer-htdm.sh htdm`
  - Expected pass: deployment created; reboot required; rollback possible with `rpm-ostree rollback`.
- BlueBuild:
  - Build using `packaging/immutable/bluebuild/module.yml` and `recipe.yml.example`.
  - Expected pass: image build succeeds and includes `htdm-*` packages.

Fail criteria:
- Wrong package-manager branch selected.
- Install path returns nonzero.
- Rollback commands fail or leave unusable deployment.

### 2) Auth Policy + PAM Boundary

Prereq: install PAM snippets and greetd config.

Procedure:
- Boot to greeter.
- Select Game Mode.
  - Expected pass: no PAM password prompt; session starts only as `gaming`.
- Select Desktop (GNOME/KDE) without auth marker.
  - Expected pass: launch denied.
- Complete PAM auth using `htdm-desktop-auth`.
  - Expected pass: desktop session launches; unauthorized users denied if allow-list set.

Fail criteria:
- Desktop launches without successful auth.
- Game mode launches under non-gaming user.
- PAM service mismatch or bypass observed.

### 3) Shared Steam Storage (Root + Multi-User)

Procedure:
- `sudo HTDM_ALLOWED_DESKTOP_USERS="alice" ./scripts/storage/setup-shared-steam.sh /var/lib/steam-shared`
- `HTDM_ALLOWED_DESKTOP_USERS="alice" ./scripts/storage/check-shared-steam-health.sh /var/lib/steam-shared`
- Write test as gaming user and desktop user:
  - `sudo -u gaming touch /var/lib/steam-shared/library/.gaming-write-test`
  - `sudo -u alice touch /var/lib/steam-shared/library/.desktop-write-test`

Expected pass:
- Health script prints `OK`.
- Both users can create files in shared library path.
- Group ownership and default ACL persist on new files.

Fail criteria:
- Missing `setgid`, missing default ACL, user not in `steamlib`, write denied for either user.

### 4) Controller Compatibility + Reconnect

For each controller type (Xbox USB/BT, DualSense USB/BT, Switch Pro, generic):

Procedure:
- Navigate greeter entirely with controller.
- Disconnect at main menu, reconnect, verify focus recovery.
- Disconnect/reconnect during desktop selection/auth UI.

Expected pass:
- Full navigation without keyboard/mouse.
- Reconnect restores usable focus within 2 seconds.
- No stuck input state or duplicate ghost inputs.

Fail criteria:
- Controller cannot complete login path.
- Reconnect requires restarting greeter/session.

### 5) Suspend/Resume Behavior

Procedure:
- From game mode: suspend (`systemctl suspend`), wake system.
- Verify quick action handling (`ReturnToGame`, `SwitchToDesktop`, `SignOutAndChooseSession`).
- From desktop: suspend and resume.

Expected pass:
- Resume state/action files update correctly.
- Game mode follows configured lock policy.
- Desktop resumes locked by DE policy.
- Session switch does not create nested compositor/session stacks.

Fail criteria:
- Lost input focus after wake.
- Wrong resume target/action.
- Graphical corruption or nested session layering.

### 6) Theme Preset and Readability

Procedure:
- Cycle all presets through greeter `Appearance`.
- Use `Reset To Recommended`.
- Validate dark/light and high-contrast readability at 10-foot distance.

Expected pass:
- All presets apply and persist.
- Reset always restores `modern-neutral`.
- Text remains readable and contrast acceptable in each preset.

Fail criteria:
- Preset apply failure, stale theme file, unreadable text in any curated preset.

## Risks / Blockers

- This environment cannot perform real PAM/greetd login path validation.
- No physical controllers, suspend/resume hardware cycle, or GPU-specific compositor checks are available here.
- `shellcheck` and `rpmspec` are unavailable in this environment, limiting deeper static packaging/lint validation.

## Next Commands for Real Hardware Testing

```bash
# 1) Fast local static sanity
cd /path/to/HTDM
bash -n scripts/session/*.sh scripts/storage/*.sh scripts/power/*.sh scripts/install/*.sh
python3 -m py_compile scripts/greeter/controller_greeter_mvp.py

# 2) Distro bootstrap dry-run then real run
sudo ./scripts/install/bootstrap.sh --dry-run
sudo ./scripts/install/bootstrap.sh

# 3) Shared Steam setup + health
sudo HTDM_ALLOWED_DESKTOP_USERS="alice" ./scripts/storage/setup-shared-steam.sh /var/lib/steam-shared
HTDM_ALLOWED_DESKTOP_USERS="alice" ./scripts/storage/check-shared-steam-health.sh /var/lib/steam-shared

# 4) Immutable host layering
sudo ./packaging/immutable/rpm-ostree/layer-htdm.sh htdm
sudo rpm-ostree rollback
```
