#!/usr/bin/env bash
# Chạy một script của công cụ với đúng trình duyệt dựng hình: ./chay.sh render.py "cho-edit/<du-an>" [tham số]
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$PATH"
export REMOTION_BROWSER="$(cat .trinh-duyet 2>/dev/null)"
export NODE_OPTIONS="--require $PWD/scripts/an-toan-node.cjs ${NODE_OPTIONS:-}"  # máy chặn đọc giao diện mạng vẫn dựng được
s="$1"; shift
exec python3 "scripts/$s" "$@"
