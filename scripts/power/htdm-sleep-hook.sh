#!/usr/bin/env bash
set -euo pipefail

action="${1:-}"
phase="${2:-}"
state_dir="${HTDM_RESUME_DIR:-/run/htdm/resume}"
state_file="${state_dir}/state.env"

mkdir -p "$state_dir"

case "$action:$phase" in
  pre:suspend|pre:hibernate)
    cat >"$state_file" <<EOF
HTDM_RESUMED=0
HTDM_LAST_SLEEP_MODE=${phase}
HTDM_LAST_EVENT_TS=$(date +%s)
EOF
    ;;
  post:suspend|post:hibernate)
    cat >"$state_file" <<EOF
HTDM_RESUMED=1
HTDM_LAST_SLEEP_MODE=${phase}
HTDM_LAST_EVENT_TS=$(date +%s)
EOF
    ;;
  *)
    printf "Ignoring unknown hook event: %s %s\n" "$action" "$phase" >&2
    ;;
esac
