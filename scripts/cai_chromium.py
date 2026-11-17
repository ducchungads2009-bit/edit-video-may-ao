"""Cài trình duyệt dựng hình dự phòng từ npm (@sparticuz/chromium) khi máy ảo không có Chrome và không tải được
Chrome từ Google / Playwright. Gói npm chứa sẵn Chromium nén brotli — chỉ cần mạng tới registry.npmjs.org (luôn được phép).
In ra đường dẫn tập lệnh bọc (chrome.sh) để ghi vào .trinh-duyet.  Dùng: python3 scripts/cai_chromium.py [thư mục đích]
"""
import io, os, subprocess, sys, tarfile, tempfile, glob

dst = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.cache/chromium-npm"))
wrap = os.path.join(dst, "chrome.sh")
if os.path.exists(wrap) and os.path.exists(os.path.join(dst, "chromium")):
    print(wrap); sys.exit(0)

try:
    import brotli
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "brotli", "--break-system-packages"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import brotli

tmp = tempfile.mkdtemp()
subprocess.run(["npm", "pack", "@sparticuz/chromium@153", "--silent"], cwd=tmp, check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
tgz = glob.glob(os.path.join(tmp, "*.tgz"))[0]
os.makedirs(dst, exist_ok=True)
with tarfile.open(tgz) as t:
    def raw(name):
        return brotli.decompress(t.extractfile(f"package/bin/{name}").read())
    with open(os.path.join(dst, "chromium"), "wb") as f:
        f.write(raw("chromium.br"))
    os.chmod(os.path.join(dst, "chromium"), 0o755)
    # thư viện đi kèm (nss, expat…) + swiftshader; KHÔNG dùng fonts.conf của gói (trỏ /var/task, /tmp/fonts -> trang bị sập)
    for n in ("al2023.tar.br", "swiftshader.tar.br"):
        with tarfile.open(fileobj=io.BytesIO(raw(n))) as s:
            s.extractall(dst, filter="data") if hasattr(tarfile, "data_filter") else s.extractall(dst)
with open(wrap, "w") as f:
    f.write('#!/bin/bash\nD="$(cd "$(dirname "$0")" && pwd)"\n'
            'export LD_LIBRARY_PATH="$D/lib:$D${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n'
            'exec "$D/chromium" --no-sandbox --disable-dev-shm-usage "$@"\n')
os.chmod(wrap, 0o755)
print(wrap)
