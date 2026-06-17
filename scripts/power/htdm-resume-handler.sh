#!/usr/bin/env bash
set -euo pipefail

state_file="${HTDM_RESUME_STATE_FILE:-/run/htdm/resume/state.env}"
action_file="${HTDM_RESUME_ACTION_FILE:-/run/htdm/resume/action}"
launcher="${HTDM_LAUNCHER:-/usr/local/lib/htdm/session/launch-session.sh}"

if [[ ! -f "$state_file" ]]; then
  exit 0
fi

# shellcheck disable=SC1090
source "$state_file"
if [[ "${HTDM_RESUMED:-0}" != "1" ]]; then
  exit 0
fi

if [[ ! -f "$action_file" ]]; then
  exit 0
fi

action="$(tr -d '\n' <"$action_file")"
case "$action" in
  return-to-game)
    exec "$launcher" game gamescope
    ;;
  switch-to-desktop)
    # Default desktop target is GNOME; user may choose KDE from greeter.
    exec "$launcher" desktop gnome
    ;;
  sign-out)
    rm -f "$action_file"
    exit 0
    ;;
  *)
    printf "Unknown resume action: %s\n" "$action" >&2
    exit 1
    ;;
esac
