#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
port="${1:-8080}"
pid_file="$root/.state/demo-${port}.pid"
if [[ ! -f "$pid_file" ]]; then
  echo "No launcher-managed demo found on port ${port}."
  exit 0
fi
pid="$(cat "$pid_file")"
if [[ -r "/proc/${pid}/cmdline" ]]; then
  command_line="$(tr '\0' ' ' < "/proc/${pid}/cmdline")"
  if [[ "$command_line" != *motionbricks-demo* ]]; then
    echo "PID ${pid} no longer belongs to MotionBricks; refusing to stop it." >&2
    exit 1
  fi
  kill "$pid"
  echo "Stopped MotionBricks on port ${port}."
fi
rm -f "$pid_file"
