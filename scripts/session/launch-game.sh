#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/common-policy.sh"

requested_session="${1:-gamescope}"
command_to_run="$(game_command_for "$requested_session" || true)"

if [[ -z "$command_to_run" ]]; then
  printf "Denied: unknown game session '%s'\n" "$requested_session" >&2
  exit 1
fi

actual_user="$(id -un)"
if [[ "$actual_user" != "$HTDM_GAMING_USER" ]]; then
  printf "Denied: game session must run as '%s' (current '%s')\n" \
    "$HTDM_GAMING_USER" "$actual_user" >&2
  exit 1
fi

# Session switch UX hook: clear pending resume action on successful game launch.
if [[ -f "$HTDM_RESUME_ACTION_FILE" ]]; then
  rm -f "$HTDM_RESUME_ACTION_FILE"
fi

exec "$command_to_run"
