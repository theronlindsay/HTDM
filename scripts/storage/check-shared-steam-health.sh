#!/usr/bin/env bash
set -euo pipefail

root="${1:-/var/lib/steam-shared}"
group="${HTDM_STEAM_GROUP:-steamlib}"
gaming_user="${HTDM_GAMING_USER:-gaming}"
desktop_users_csv="${HTDM_ALLOWED_DESKTOP_USERS:-}"

if [[ ! -d "$root/library" ]]; then
  printf "FAIL: missing library directory at %s/library\n" "$root" >&2
  exit 1
fi

group_on_root="$(stat -c '%G' "$root")"
if [[ "$group_on_root" != "$group" ]]; then
  printf "FAIL: %s group is %s, expected %s\n" "$root" "$group_on_root" "$group" >&2
  exit 1
fi

mode="$(stat -c '%a' "$root/library")"
if [[ "${mode:0:1}" != "2" ]]; then
  printf "FAIL: setgid bit missing on %s/library (mode %s)\n" "$root" "$mode" >&2
  exit 1
fi

if ! id -nG "$gaming_user" | tr ' ' '\n' | rg -q "^${group}$"; then
  printf "FAIL: gaming user %s is not in %s\n" "$gaming_user" "$group" >&2
  exit 1
fi

IFS=',' read -r -a desktop_users <<<"$desktop_users_csv"
for user in "${desktop_users[@]}"; do
  user="${user#"${user%%[![:space:]]*}"}"
  user="${user%"${user##*[![:space:]]}"}"
  if [[ -n "$user" ]] && ! id -nG "$user" | tr ' ' '\n' | rg -q "^${group}$"; then
    printf "FAIL: desktop user %s is not in %s\n" "$user" "$group" >&2
    exit 1
  fi
done

if ! getfacl -p "$root/library" | rg -q "^default:group:${group}:rwx$"; then
  printf "FAIL: default ACL for group %s not present on %s/library\n" "$group" "$root" >&2
  exit 1
fi

printf "OK: shared Steam storage policy healthy at %s\n" "$root"
