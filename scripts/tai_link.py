"""Tải file từ link người dùng gửi (Google Drive file / thư mục, Dropbox, link tải thẳng) vào một thư mục.
Dùng: python3 scripts/tai_link.py "<thư mục đích>" <link> [<link> ...]
Drive: phải chia sẻ "Bất kỳ ai có đường liên kết". Claude: cần cho phép tên miền drive.google.com, drive.usercontent.google.com
(Cài đặt → Capabilities); ChatGPT chế độ Công việc thường đã mở mạng. In ra từng file đã tải hoặc lỗi dễ hiểu."""
import os, re, sys, subprocess, urllib.request, urllib.parse

dst = os.path.abspath(sys.argv[1]); links = sys.argv[2:]
os.makedirs(dst, exist_ok=True)
ok = bad = 0
for u in links:
    u = u.strip().strip("<>").rstrip(".,;)")
    try:
        def all_files():
            return {os.path.relpath(os.path.join(r, f), dst) for r, _, fs in os.walk(dst) for f in fs}
        before = all_files()
        if "drive.google.com" in u or "docs.google.com" in u:
            import gdown
            if "/folders/" in u:
                got = gdown.download_folder(url=u, output=dst, quiet=True, remaining_ok=True) or []
                if len(got) >= 50:
                    print("LƯU Ý: Drive chỉ cho tải tối đa 50 file mỗi thư mục — thư mục nào nhiều hơn thì chia nhỏ hoặc gửi link từng thư mục")
            else:
                try:
                    out = gdown.download(url=u, output=dst + os.sep, quiet=True, fuzzy=True)
                except TypeError:  # gdown >= 5: tự nhận link dạng /file/d/…
                    out = gdown.download(url=u, output=dst + os.sep, quiet=True)
                if not out:
                    raise RuntimeError("Drive không cho tải — kiểm tra đã chia sẻ 'Bất kỳ ai có đường liên kết' chưa")
        else:
            if "dropbox.com" in u:
                u = re.sub(r"([?&])dl=0", r"\1dl=1", u) if "dl=0" in u else u + ("&" if "?" in u else "?") + "dl=1"
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                name = None
                cd = r.headers.get("Content-Disposition") or ""
                m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", cd)
                if m:
                    name = urllib.parse.unquote(m.group(1))
                name = os.path.basename(name or urllib.parse.urlparse(u).path) or "tai-ve"
                with open(os.path.join(dst, name), "wb") as f:
                    while True:
                        b = r.read(1 << 20)
                        if not b:
                            break
                        f.write(b)
        new = sorted(all_files() - before)
        for n in new:
            print(f"ĐÃ TẢI: {n} ({os.path.getsize(os.path.join(dst, n)) / 1e6:.1f} MB)")
        ok += 1
    except Exception as e:
        msg = str(e)
        if "403" in msg or "Forbidden" in msg or "Tunnel" in msg or "URLError" in type(e).__name__:
            host = urllib.parse.urlparse(u).netloc
            need = "drive.google.com, drive.usercontent.google.com" if "google" in host else ("www.dropbox.com, dl.dropboxusercontent.com" if "dropbox" in host else host)
            msg = f"máy ảo không vào được trang này (Claude: cho phép tên miền {need} trong Cài đặt → Capabilities, rồi mở chat mới)"
        print(f"LỖI: {u} — {msg}")
        bad += 1
print(f"Xong: {ok} link tải được, {bad} link lỗi.")
