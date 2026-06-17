#!/usr/bin/env bash
set -euo pipefail

root="${1:-/var/lib/steam-shared}"
group="${HTDM_STEAM_GROUP:-steamlib}"
gaming_user="${HTDM_GAMING_USER:-gaming}"
desktop_users_csv="${HTDM_ALLOWED_DESKTOP_USERS:-}"

if ! command -v setfacl >/dev/null 2>&1 || ! command -v getfacl >/dev/null 2>&1; then
  printf "Missing ACL tools (setfacl/getfacl). Install acl package.\n" >&2
  exit 1
fi

if ! getent group "$group" >/dev/null; then
  groupadd --system "$group"
fi

usermod -aG "$group" "$gaming_user"

IFS=',' read -r -a desktop_users <<<"$desktop_users_csv"
for user in "${desktop_users[@]}"; do
  user="${user#"${user%%[![:space:]]*}"}"
  user="${user%"${user##*[![:space:]]}"}"
  if [[ -n "$user" ]]; then
    usermod -aG "$group" "$user"
  fi
done

install -d -m 2775 -o root -g "$group" "$root"
install -d -m 2775 -o root -g "$group" "$root/library"
install -d -m 2775 -o root -g "$group" "$root/compatdata"
install -d -m 2775 -o root -g "$group" "$root/shadercache"

setfacl -R -m "g:${group}:rwx" "$root"
setfacl -R -d -m "g:${group}:rwx" "$root"

printf "Configured shared Steam storage at %s with group %s\n" "$root" "$group"
