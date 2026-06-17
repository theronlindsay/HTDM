# Packaging, Install, and Rollback Assumptions

This document defines packaging and install scaffolding for the HTDM Phase 1
foundation and the assumptions for mutable and immutable targets.

## Packaging Matrix

| Family | Deliverable | Path |
| --- | --- | --- |
| Fedora/RHEL | RPM spec scaffold (`htdm-core`, `htdm-config`, `htdm-installer`) | `packaging/rpm/htdm.spec` |
| Debian/Ubuntu | DEB source scaffold (`control`, `rules`, maintainer scripts) | `packaging/deb/` |
| Arch | PKGBUILD scaffold with split package outputs | `packaging/arch/PKGBUILD` |
| Fedora Atomic | rpm-ostree layering notes + helper script | `packaging/immutable/rpm-ostree/` |
| BlueBuild-based images | Reusable module + recipe example | `packaging/immutable/bluebuild/` |

## Package Split Intent

- `htdm-core`:
  - Session wrapper scripts.
  - Shared policy defaults.
- `htdm-config`:
  - PAM services, `greetd` example, systemd preset, tmpfiles, sysusers.
- `htdm-installer`:
  - Bootstrap tooling for distro detection and applying defaults.

## Installer and Provisioning Assumptions

- Bootstrap entrypoint: `scripts/install/bootstrap.sh`.
- Distro detection is based on `/etc/os-release` (`ID`, `ID_LIKE`).
- Installer supports:
  - RPM family package managers (`dnf`, `yum`, `rpm-ostree`).
  - DEB family (`apt-get`).
  - Arch family (`pacman`).
- Installer defaults to non-destructive behavior and supports `--dry-run`.

## System Presets and Templates

- `config/systemd-preset/90-htdm.preset` enables `greetd.service` and
  `htdm-firstboot-setup.service` by default.
- `config/systemd/htdm-firstboot-setup.service` provides a one-shot setup hook.
- `config/tmpfiles/htdm.conf` creates shared runtime/data directories.
- `config/sysusers/htdm.conf` defines `gaming` user and `steamlib` group.

## Rollback Assumptions

- Mutable systems:
  - Roll back by downgrading or removing HTDM packages via native package manager.
  - Preset and tmpfiles/sysusers artifacts are declarative and recreated on install.
- Immutable systems:
  - `rpm-ostree` rollback uses deployment rollback (`rpm-ostree rollback`).
  - BlueBuild rollback uses previous OCI image deployment pin.

## CI Packaging

- GitHub Actions workflows in `.github/workflows/` build RPM and DEB packages
  directly from this repository scaffold.
- Workflows run on push, tag (`v*`), and manual dispatch.
- Artifacts are uploaded for each run; on tag builds, workflows draft a release
  and attach package assets.

## Bazzite Install Notes

- Treat HTDM as layered content via `rpm-ostree`.
- Install all split RPMs together (`htdm-core`, `htdm-config`,
  `htdm-installer`) and reboot into the new deployment.
- Prefer release artifacts for reproducible installs; use local `rpmbuild`
  output for development testing.

## Dependencies on Core Implementation

- Installer and package templates assume wrapper scripts already exist:
  - `scripts/session/launch-game.sh`
  - `scripts/session/launch-desktop.sh`
  - `scripts/session/common-policy.sh`
- Packaging does not assume custom greeter UI is complete yet; templates keep
  `tuigreet`/placeholder command paths where needed.
