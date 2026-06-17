#!/usr/bin/env bash
set -euo pipefail

POLICY_FILE="${HTDM_POLICY_FILE:-/etc/htdm/session-policy.env}"

if [[ -f "$POLICY_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$POLICY_FILE"
fi

: "${HTDM_GAMING_USER:=gaming}"
: "${HTDM_AUTH_MARKER_ENV:=HTDM_DESKTOP_AUTH_OK}"
: "${HTDM_DESKTOP_SESSION_GNOME:=gnome:gnome-session}"
: "${HTDM_DESKTOP_SESSION_KDE:=kde:startplasma-wayland}"
: "${HTDM_GAME_SESSION:=gamescope:gamescope-session}"
: "${HTDM_ALLOWED_DESKTOP_USERS:=}"
: "${HTDM_THEME_PRESET_FILE:=/etc/htdm/themes/presets.json}"
: "${HTDM_CURRENT_THEME_FILE:=/var/lib/htdm/theme/current-theme.json}"
: "${HTDM_RESUME_STATE_FILE:=/run/htdm/resume/state.env}"
: "${HTDM_RESUME_ACTION_FILE:=/run/htdm/resume/action}"

resolve_command_from_pair() {
  local pair="$1"
  local key="$2"

  local id="${pair%%:*}"
  local cmd="${pair#*:}"

  if [[ "$id" == "$key" && -n "$cmd" ]]; then
    printf "%s" "$cmd"
    return 0
  fi

  return 1
}

csv_has_value() {
  local csv="$1"
  local needle="$2"
  local item=""

  IFS=',' read -r -a items <<<"$csv"
  for item in "${items[@]}"; do
    item="${item#"${item%%[![:space:]]*}"}"
    item="${item%"${item##*[![:space:]]}"}"
    if [[ -n "$item" && "$item" == "$needle" ]]; then
      return 0
    fi
  done

  return 1
}

desktop_user_allowed() {
  local user="$1"

  if [[ -z "$HTDM_ALLOWED_DESKTOP_USERS" ]]; then
    return 0
  fi

  csv_has_value "$HTDM_ALLOWED_DESKTOP_USERS" "$user"
}

desktop_command_for() {
  local requested="$1"
  local cmd=""

  if cmd="$(resolve_command_from_pair "$HTDM_DESKTOP_SESSION_GNOME" "$requested")"; then
    printf "%s\n" "$cmd"
    return 0
  fi

  if cmd="$(resolve_command_from_pair "$HTDM_DESKTOP_SESSION_KDE" "$requested")"; then
    printf "%s\n" "$cmd"
    return 0
  fi

  return 1
}

game_command_for() {
  local requested="$1"
  local cmd=""

  if cmd="$(resolve_command_from_pair "$HTDM_GAME_SESSION" "$requested")"; then
    printf "%s\n" "$cmd"
    return 0
  fi

  return 1
}
