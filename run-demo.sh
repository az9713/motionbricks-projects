#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
port="${1:-8080}"
cd "$root/motion-bricks.cpp"
mkdir -p "$root/.state"
echo "$$" > "$root/.state/demo-${port}.pid"
exec ./build/wsl-cpu/bin/motionbricks-demo \
  -listen "127.0.0.1:${port}" \
  -library ./build/wsl-cpu/libmotionbricks.so \
  -model ./generated/g1-f32 \
  -styles ./generated/styles \
  -device cpu >> "$root/.state/demo-${port}.log" 2>&1
