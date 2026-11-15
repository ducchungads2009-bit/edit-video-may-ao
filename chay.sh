#!/usr/bin/env bash
# Chạy một script của công cụ với đúng trình duyệt dựng hình: ./chay.sh render.py "cho-edit/<du-an>" [tham số]
cd "$(dirname "$0")"
export REMOTION_BROWSER="$(cat .trinh-duyet 2>/dev/null)"
s="$1"; shift
exec python3 "scripts/$s" "$@"
