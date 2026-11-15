#!/usr/bin/env bash
# Cài công cụ dựng video trên máy ảo của Claude (chạy 1 lần mỗi phiên, ~1–2 phút). In "SẴN SÀNG" khi xong.
set -e
cd "$(dirname "$0")"
echo "== Thư viện Python"
pip install --break-system-packages -q sherpa-onnx soundfile numpy opencv-python-headless onnxruntime 2>&1 | grep -v -i "warning\|notice" || true
echo "== Thư viện dựng (npm)"
npm ci --no-audit --no-fund --loglevel=error
echo "== Mô hình nhận giọng tiếng Việt"
if [ ! -f models/sherpa-onnx-zipformer-vi-2025-04-20/tokens.txt ]; then
  curl -sSL --retry 3 https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-zipformer-vi-2025-04-20.tar.bz2 | tar xj -C models
fi
echo "== Trình duyệt để dựng hình"
B=""
for c in google-chrome google-chrome-stable chromium chromium-browser; do command -v $c >/dev/null 2>&1 && { B=$(command -v $c); break; }; done
if [ -z "$B" ]; then
  npx --yes playwright@1 install chromium >/dev/null 2>&1 || true
  B=$(ls -d ~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome 2>/dev/null | head -1)
fi
[ -n "$B" ] || { echo "LỖI: không tìm được trình duyệt Chrome/Chromium để dựng hình"; exit 1; }
echo "$B" > .trinh-duyet
command -v ffmpeg >/dev/null || { echo "LỖI: máy ảo thiếu ffmpeg"; exit 1; }
echo "== Kiểm tra mạng cho các tính năng cần Internet"
chk() { c=$(curl -s -o /dev/null -m 8 -w "%{http_code}" "$1"); [ "$c" != "000" ] && [ "$c" != "403" ] && echo co || echo khong; }
BD=$(chk https://tiles.openfreemap.org/styles/liberty); TD=$(chk https://nominatim.openstreetmap.org/search?q=Hanoi\&format=json)
VT=$(chk https://tiles.maps.eox.at/wmts/1.0.0/WMTSCapabilities.xml); PX=$(chk https://pixabay.com/api/); OV=$(chk https://api.openverse.org/v1/images/?q=hanoi)
printf '{"banDo": "%s", "timToaDo": "%s", "veTinh": "%s", "stockPixabay": "%s", "anhDiaDanh": "%s"}\n' $BD $TD $VT $PX $OV > .mang.json
echo "   bản đồ: $BD · tìm toạ độ: $TD · bản đồ vệ tinh: $VT · ảnh/video stock: $PX · ảnh địa danh: $OV"
[ "$BD$TD" = "coco" ] || echo "   (Muốn dùng khối bản đồ: thêm các tên miền ở mục KHỐI CẦN MẠNG vào danh sách được phép trong cài đặt Claude)"
mkdir -p cho-edit
echo "SẴN SÀNG — trình duyệt: $B"
