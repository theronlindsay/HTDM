#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/distro-detect.sh"

dry_run=0
if [[ "${1:-}" == "--dry-run" ]]; then
  dry_run=1
fi

run_cmd() {
  if [[ "$dry_run" -eq 1 ]]; then
    printf '[dry-run] %s\n' "$*"
  else
    "$@"
  fi
}

detect_distro_family
printf 'Detected distro family: %s\n' "${HTDM_DISTRO_FAMILY}"

case "${HTDM_DISTRO_FAMILY}" in
  rpm)
    if command -v rpm-ostree >/dev/null 2>&1 && rpm-ostree status >/dev/null 2>&1; then
      run_cmd rpm-ostree install htdm-core htdm-config htdm-installer
      printf 'Reboot required for rpm-ostree deployments.\n'
    elif command -v dnf >/dev/null 2>&1; then
      run_cmd dnf install -y htdm-core htdm-config htdm-installer
    elif command -v yum >/dev/null 2>&1; then
      run_cmd yum install -y htdm-core htdm-config htdm-installer
    else
      printf 'No supported RPM package manager found.\n' >&2
      exit 1
    fi
    ;;
  deb)
    run_cmd apt-get update
    run_cmd apt-get install -y htdm-core htdm-config htdm-installer
    ;;
  arch)
    run_cmd pacman -Sy --noconfirm htdm-core htdm-config htdm-installer
    ;;
  *)
    printf 'Unsupported distro family: %s\n' "${HTDM_DISTRO_FAMILY}" >&2
    exit 1
    ;;
esac

run_cmd "${SCRIPT_DIR}/apply-defaults.sh"
printf 'HTDM bootstrap complete.\n'
