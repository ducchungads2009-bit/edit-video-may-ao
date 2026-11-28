#!/usr/bin/env bash
# Cài công cụ dựng video trên máy ảo (Claude, hoặc ChatGPT chế độ Công việc) — 1 lần mỗi phiên, ~1–2 phút. In "SẴN SÀNG" khi xong.
set -e
cd "$(dirname "$0")"
mkdir -p ~/.local/bin; export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$PATH"
# Máy ảo thiếu Node / ffmpeg (vd ChatGPT) -> tải bản dựng sẵn (cần mạng tới nodejs.org / johnvansickle.com)
# bộ dựng HyperFrames cần Node ≥ 22.12
node_du() { command -v npm >/dev/null 2>&1 && node -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(a>22||(a===22&&b>=12)?0:1)' 2>/dev/null; }
if ! node_du; then
  echo "== Tải Node.js 22"
  NV=v22.12.0
  curl -sSL --retry 3 https://nodejs.org/dist/$NV/node-$NV-linux-x64.tar.xz | tar xJ -C /tmp && rm -rf ~/.local/node && mv /tmp/node-$NV-linux-x64 ~/.local/node
  hash -r
fi
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "== Tải ffmpeg"
  curl -sSL --retry 3 https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar xJ -C /tmp \
    && cp /tmp/ffmpeg-*-amd64-static/ffmpeg /tmp/ffmpeg-*-amd64-static/ffprobe ~/.local/bin/ || true
fi
echo "== Thư viện Python"
PKGS="sherpa-onnx soundfile numpy opencv-python-headless onnxruntime pillow brotli gdown fonttools"
{ python3 -m pip install --break-system-packages -q $PKGS 2>/dev/null || python3 -m pip install -q $PKGS; } 2>&1 | grep -v -i "warning\|notice" || true
echo "== Thư viện dựng (npm)"
npm ci --no-audit --no-fund --loglevel=error
python3 scripts/canh_ai.py lib >/dev/null 2>&1 || echo "   (chưa dựng được thư viện cảnh AI — canh_ai.py tự dựng khi cần)"
echo "== Mô hình nhận giọng tiếng Việt"
if [ ! -f models/sherpa-onnx-zipformer-vi-2025-04-20/tokens.txt ]; then
  curl -sSL --retry 3 https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-zipformer-vi-2025-04-20.tar.bz2 | tar xj -C models
fi
echo "== Trình duyệt để dựng hình"
B=""
# Tìm trình duyệt dựng hình: có sẵn trên máy -> bản Playwright/Puppeteer đã cài sẵn -> tải (nếu mạng cho phép).
# Mỗi ứng viên phải CHẠY THẬT được (máy ảo ChatGPT có "chromium" chỉ là lệnh mồi, thiếu tập tin chạy).
chay_duoc() { [ -x "$1" ] && timeout 30 "$1" --headless --no-sandbox --disable-gpu --dump-dom "data:text/html,<p>ok-chay</p>" 2>/dev/null | grep -q ok-chay; }
tim() { B=""
  for c in $(for n in google-chrome google-chrome-stable chromium chromium-browser chrome headless_shell chrome-headless-shell; do command -v $n 2>/dev/null; done) \
           $(ls -d ${PLAYWRIGHT_BROWSERS_PATH:-/nonexist}/chromium*/chrome-linux*/{chrome,headless_shell} /opt/pw-browsers/chromium*/chrome-linux*/{chrome,headless_shell} \
       ~/.cache/ms-playwright/chromium*/chrome-linux*/{chrome,headless_shell} ~/.cache/puppeteer/chrome*/linux-*/chrome-*/{chrome,chrome-headless-shell} \
       ~/.cache/chs/*/chrome-headless-shell-linux64/chrome-headless-shell /usr/lib/chromium/chromium /opt/google/chrome/chrome 2>/dev/null); do
    chay_duoc "$c" && { B="$c"; return; }
  done; }
# tải thẳng Chrome Headless Shell (Chrome for Testing) bằng curl — đi được qua proxy của máy ảo khi trình cài Puppeteer bị timeout
tai_chs() { v=131.0.6778.204; d=~/.cache/chs/$v; [ -x $d/chrome-headless-shell-linux64/chrome-headless-shell ] && return
  mkdir -p $d && curl -sSL --retry 2 -m 240 -o /tmp/chs.zip "https://storage.googleapis.com/chrome-for-testing-public/$v/linux64/chrome-headless-shell-linux64.zip" \
    && python3 -c "import zipfile,sys;zipfile.ZipFile('/tmp/chs.zip').extractall(sys.argv[1])" $d && chmod +x $d/chrome-headless-shell-linux64/chrome-headless-shell; rm -f /tmp/chs.zip; }
[ -n "$EP_DU_PHONG" ] && B="" || tim
if [ -z "$B" ]; then
  echo "   (máy ảo chưa có trình duyệt chạy được — đang thử tải…)"
  timeout 180 npx --yes playwright@1 install chromium-headless-shell >/dev/null 2>&1 || timeout 180 npx --yes playwright@1 install chromium >/dev/null 2>&1 || true
  tim
fi
if [ -z "$B" ]; then tai_chs; tim; fi
if [ -z "$B" ]; then
  timeout 180 npx --yes @puppeteer/browsers install chrome-headless-shell@stable --path ~/.cache/puppeteer >/dev/null 2>&1 || true
  tim
fi
if [ -z "$B" ]; then   # cách cuối: Chromium nén sẵn trong gói npm (chỉ cần registry npm)
  C=$(timeout 240 python3 scripts/cai_chromium.py 2>/dev/null | tail -1)
  chay_duoc "$C" && B="$C"
fi
[ -n "$B" ] || { echo "LỖI: không tìm được trình duyệt Chrome/Chromium để dựng hình"; exit 1; }
echo "$B" > .trinh-duyet
command -v ffmpeg >/dev/null || { echo "LỖI: máy ảo thiếu ffmpeg"; exit 1; }
echo "== Kiểm tra mạng cho các tính năng cần Internet"
chk() { c=$(curl -s -o /dev/null -m 8 -w "%{http_code}" "$1"); [ "$c" != "000" ] && [ "$c" != "403" ] && echo co || echo khong; }
BD=$(chk https://tiles.openfreemap.org/styles/liberty); TD=$(chk https://nominatim.openstreetmap.org/search?q=Hanoi\&format=json)
VT=$(chk https://tiles.maps.eox.at/wmts/1.0.0/WMTSCapabilities.xml); PX=$(chk https://pixabay.com/api/); OV=$(chk https://api.openverse.org/v1/images/?q=hanoi); DR=$(chk https://drive.usercontent.google.com/)
printf '{"banDo": "%s", "timToaDo": "%s", "veTinh": "%s", "stockPixabay": "%s", "anhDiaDanh": "%s", "linkDrive": "%s"}\n' $BD $TD $VT $PX $OV $DR > .mang.json
echo "   bản đồ: $BD · tìm toạ độ: $TD · bản đồ vệ tinh: $VT · ảnh/video stock: $PX · ảnh địa danh: $OV · tải link Drive: $DR"
[ "$BD$TD" = "coco" ] || echo "   (Muốn dùng khối bản đồ: thêm các tên miền ở mục KHỐI CẦN MẠNG vào danh sách được phép trong cài đặt Claude)"
mkdir -p cho-edit
echo "SẴN SÀNG — trình duyệt: $B"
