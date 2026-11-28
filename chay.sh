#!/usr/bin/env bash
# Chạy một script của công cụ với đúng trình duyệt dựng hình: ./chay.sh render.py "cho-edit/<du-an>" [tham số]
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$PATH"
export REMOTION_BROWSER="$(cat .trinh-duyet 2>/dev/null)"
export NODE_OPTIONS="--require $PWD/scripts/an-toan-node.cjs ${NODE_OPTIONS:-}"  # máy chặn đọc giao diện mạng vẫn dựng được
# tắt mọi gửi số liệu sử dụng (máy ảo ChatGPT chặn lượt chạy khi thấy kết nối telemetry)
export DO_NOT_TRACK=1 HF_HUB_DISABLE_TELEMETRY=1 HYPERFRAMES_NO_TELEMETRY=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
  NEXT_TELEMETRY_DISABLED=1 ORT_DISABLE_TELEMETRY=1 PUPPETEER_SKIP_DOWNLOAD=1
s="$1"; shift
exec python3 "scripts/$s" "$@"
