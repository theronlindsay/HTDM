#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/common-policy.sh"

requested_session="${1:-}"
if [[ -z "$requested_session" ]]; then
  printf "Denied: desktop session id is required\n" >&2
  exit 1
fi

auth_value="${!HTDM_AUTH_MARKER_ENV:-}"
if [[ "$auth_value" != "1" ]]; then
  printf "Denied: missing desktop auth marker '%s'\n" "$HTDM_AUTH_MARKER_ENV" >&2
  exit 1
fi

current_user="$(id -un)"
if ! desktop_user_allowed "$current_user"; then
  printf "Denied: desktop user '%s' is not in HTDM_ALLOWED_DESKTOP_USERS\n" "$current_user" >&2
  exit 1
fi

command_to_run="$(desktop_command_for "$requested_session" || true)"
if [[ -z "$command_to_run" ]]; then
  printf "Denied: unknown desktop session '%s'\n" "$requested_session" >&2
  exit 1
fi

# Session switch UX hook: clear pending resume action on successful desktop switch.
if [[ -f "$HTDM_RESUME_ACTION_FILE" ]]; then
  rm -f "$HTDM_RESUME_ACTION_FILE"
fi

exec "$command_to_run"
