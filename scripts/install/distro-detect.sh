#!/usr/bin/env bash
set -euo pipefail

HTDM_DISTRO_FAMILY="unknown"

detect_distro_family() {
  local os_release="/etc/os-release"
  local id_like=""
  local id=""

  if [[ -r "${os_release}" ]]; then
    # shellcheck disable=SC1090
    source "${os_release}"
    id="${ID:-}"
    id_like="${ID_LIKE:-}"
  fi

  case " ${id} ${id_like} " in
    *" fedora "*|*" rhel "*|*" centos "*|*" rocky "*|*" almalinux "*|*" opensuse "*)
      HTDM_DISTRO_FAMILY="rpm"
      ;;
    *" debian "*|*" ubuntu "*|*" linuxmint "*|*" pop "*)
      HTDM_DISTRO_FAMILY="deb"
      ;;
    *" arch "*|*" manjaro "*)
      HTDM_DISTRO_FAMILY="arch"
      ;;
    *)
      HTDM_DISTRO_FAMILY="unknown"
      ;;
  esac
}
