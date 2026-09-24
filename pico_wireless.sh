#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$ROOT/config.env" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/config.env"
fi
IP_FILE="$ROOT/.pico_wireless_ip"
PORT=5555
SERVER_PORT=${ROBODOJO_PORT:-8443}
ADB=${ROBODOJO_ADB:-$(command -v adb 2>/dev/null || true)}
[[ -n "$ADB" && -x "$ADB" ]] || { printf 'adb not found.\n' >&2; exit 2; }

usb_device() {
  "$ADB" devices | awk 'NR > 1 && $2 == "device" && $1 !~ /:/ {print $1; exit}'
}

pico_ip() {
  "$ADB" -s "$1" shell ip route | tr -d '\r' | awk '/ dev wlan0 / {print $NF; exit}'
}

connect_wifi() {
  local ip="$1"
  "$ADB" connect "$ip:$PORT" >/dev/null
  "$ADB" -s "$ip:$PORT" get-state >/dev/null
  "$ADB" -s "$ip:$PORT" reverse "tcp:$SERVER_PORT" "tcp:$SERVER_PORT"
  printf '%s\n' "$ip" >"$IP_FILE"
  printf 'Pico wireless ADB ready: %s:%s\n' "$ip" "$PORT"
  if [[ -s "$ROOT/web_token.txt" ]]; then
    printf 'Open in VR Browser: http://127.0.0.1:%s/#token=%s\n' "$SERVER_PORT" "$(tr -d '[:space:]' <"$ROOT/web_token.txt")"
  fi
}

case "${1:-}" in
  setup)
    serial="$(usb_device)"
    [[ -n "$serial" ]] || { printf 'No authorized USB Pico found.\n' >&2; exit 1; }
    ip="$(pico_ip "$serial")"
    [[ -n "$ip" ]] || { printf 'Pico wlan0 has no IPv4 address.\n' >&2; exit 1; }
    "$ADB" -s "$serial" tcpip "$PORT" >/dev/null
    connect_wifi "$ip"
    ;;
  connect)
    [[ -s "$IP_FILE" ]] || { printf 'Run %s setup once with USB connected.\n' "$0" >&2; exit 1; }
    connect_wifi "$(tr -d '[:space:]' <"$IP_FILE")"
    ;;
  *)
    printf 'Usage: %s {setup|connect}\n' "$0" >&2
    exit 2
    ;;
esac
