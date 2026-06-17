#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "apply-defaults.sh must run as root." >&2
  exit 1
fi

if command -v systemd-sysusers >/dev/null 2>&1; then
  systemd-sysusers /usr/share/htdm/config/sysusers/htdm.conf || true
fi

if command -v systemd-tmpfiles >/dev/null 2>&1; then
  systemd-tmpfiles --create /usr/share/htdm/config/tmpfiles/htdm.conf || true
fi

if command -v install >/dev/null 2>&1; then
  install -d -m 0755 /etc/htdm
fi

if [[ -f /usr/share/htdm/config/policy/session-policy.env.example ]]; then
  install -m 0644 /usr/share/htdm/config/policy/session-policy.env.example \
    /etc/htdm/session-policy.env
fi

if [[ -f /usr/share/htdm/config/configurator/configurator.json.example ]]; then
  install -m 0644 /usr/share/htdm/config/configurator/configurator.json.example \
    /etc/htdm/configurator.json
fi

if command -v systemctl >/dev/null 2>&1; then
  systemctl preset greetd.service htdm-firstboot-setup.service >/dev/null 2>&1 || true
fi

echo "HTDM defaults applied."
