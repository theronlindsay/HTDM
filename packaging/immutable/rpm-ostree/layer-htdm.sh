#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

if ! command -v rpm-ostree >/dev/null 2>&1; then
  echo "rpm-ostree not found; this host is likely not immutable Fedora-family." >&2
  exit 1
fi

PKG_NAME="${1:-htdm}"

echo "Layering package '${PKG_NAME}'..."
rpm-ostree install "${PKG_NAME}"

cat <<'EOF'
Layering complete.
Reboot into the new deployment and verify:
  - greetd status
  - htdm-firstboot-setup.service outcome
Use `rpm-ostree rollback` for immediate deployment rollback if needed.
EOF
