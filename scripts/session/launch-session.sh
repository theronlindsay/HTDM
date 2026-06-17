#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

mode="${1:-}"
session_id="${2:-}"

if [[ -z "$mode" ]]; then
  printf "Usage: %s <game|desktop> [session-id]\n" "$0" >&2
  exit 1
fi

case "$mode" in
  game)
    exec "$SCRIPT_DIR/launch-game.sh" "${session_id:-gamescope}"
    ;;
  desktop)
    if [[ -z "$session_id" ]]; then
      printf "Denied: desktop mode requires a session id (gnome or kde)\n" >&2
      exit 1
    fi
    exec "$SCRIPT_DIR/launch-desktop.sh" "$session_id"
    ;;
  *)
    printf "Denied: unsupported mode '%s'\n" "$mode" >&2
    exit 1
    ;;
esac
