# HTDM Foundation (Phase 1)

This repository contains the Phase 1 foundation for a greetd-first,
controller-first HTPC display manager architecture.

## What is in scope

- Base stack choice: greetd-first.
- Session policy boundaries: unauthenticated game mode vs authenticated desktop.
- Controller-first greeter MVP with tile navigation and Appearance menu.
- Theme token preset system with curated defaults.
- Config scaffolding for greetd and PAM service split.
- Fail-closed launcher wrappers and session router.
- Shared Steam storage setup plus health-check scripts (group/ACL model).
- Suspend/hibernate hooks and post-resume session-switch wiring.
- Packaging scaffolding for RPM/DEB/Arch deliverables.
- Immutable distro scaffolding for rpm-ostree and BlueBuild.
- Bootstrap installer scripts and deployment presets (systemd/tmpfiles/sysusers).

See `docs/architecture/phase1-foundation.md` for architecture details.
See `docs/deployment/packaging-installation.md` for packaging assumptions.

## Installation

This repo currently ships package scaffolding, not distro-hosted repositories.
Install by building packages locally from git, or by using CI/release artifacts.

### Fedora/RHEL (RPM)

1. Install build dependencies:
   - `sudo dnf install -y rpm-build`
2. Build RPMs from this repository:
   - `rpmbuild -bb packaging/rpm/htdm.spec --define "_topdir $PWD/.rpmbuild" --define "_sourcedir $PWD"`
3. Install generated packages:
   - `sudo dnf install -y .rpmbuild/RPMS/noarch/htdm-core-*.noarch.rpm .rpmbuild/RPMS/noarch/htdm-config-*.noarch.rpm .rpmbuild/RPMS/noarch/htdm-installer-*.noarch.rpm`

### Debian/Ubuntu (DEB)

1. Install build dependencies:
   - `sudo apt-get update`
   - `sudo apt-get install -y build-essential debhelper devscripts fakeroot`
2. Prepare a temporary Debian build tree and build:
   - `tmpdir="$(mktemp -d)"`
   - `rsync -a --exclude .git ./ "$tmpdir/"`
   - `mkdir -p "$tmpdir/debian" && cp -a packaging/deb/. "$tmpdir/debian/"`
   - `(cd "$tmpdir" && chmod +x debian/rules && dpkg-buildpackage -us -uc -b)`
3. Install generated packages:
   - `sudo dpkg -i "$tmpdir"/../htdm-core_*_all.deb "$tmpdir"/../htdm-config_*_all.deb "$tmpdir"/../htdm-installer_*_all.deb`

### Arch Linux

`packaging/arch/PKGBUILD` is provided as scaffolding for split packages. Build and
install using your normal PKGBUILD workflow (`makepkg` / repo tooling).

### Bazzite and other rpm-ostree systems

Bazzite users should layer the RPM artifacts and reboot into the new deployment.

From locally built RPMs:

- `sudo rpm-ostree install .rpmbuild/RPMS/noarch/htdm-core-*.rpm .rpmbuild/RPMS/noarch/htdm-config-*.rpm .rpmbuild/RPMS/noarch/htdm-installer-*.rpm`
- `systemctl reboot`

From GitHub release assets:

- Download `htdm-core`, `htdm-config`, and `htdm-installer` RPM artifacts.
- `sudo rpm-ostree install ./htdm-core-*.rpm ./htdm-config-*.rpm ./htdm-installer-*.rpm`
- `systemctl reboot`

Rollback:

- `sudo rpm-ostree rollback`
- `systemctl reboot`

## CI package builds

GitHub Actions workflows under `.github/workflows` build RPM and DEB artifacts on:

- pushes,
- tags (`v*`),
- manual dispatch.

On version tags, workflows also draft a GitHub release and attach built artifacts.

## Desktop Configurator GUI

HTDM includes a lightweight desktop settings app:

- Launch: `python3 scripts/configurator/htdm_configurator.py`
- Tech: Python standard library plus `tkinter` (no extra Python dependencies)
- Layout: left sidebar categories plus right-pane controls
- Controller basics: D-pad/left-stick navigation, A activate, B back (when
  joystick devices are exposed as `/dev/input/js*`)

See `docs/configuration/desktop-configurator.md` for persistence mappings,
validation behavior, and launch options.
