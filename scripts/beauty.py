"""LÀM ĐẸP NGƯỜI trong video: làm mịn da, sáng da, son môi, má hồng, độ nét.

plan.json -> "beauty": {"smooth": 0-100, "bright": 0-100, "lip": 0-100, "lipColor": "#C2185B",
                        "blush": 0-100, "blushColor": "#FF6F91", "sharpen": 0-100}
render.py tự xử lý trước khi xuất (lưu sẵn _work/beauty_<mã>.mp4, lần sau dùng lại); chỉ xử lý các đoạn được dùng.

Dùng:  python scripts/beauty.py "<folder>"                 xử lý theo plan.json
       python scripts/beauty.py "<folder>" --xem <giây>     ảnh trước/sau ở giây đó của video gốc -> _work/beauty_xem.jpg
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
CASCADE = ROOT / "models" / "haarcascade_frontalface_default.xml"
KEYS = ("smooth", "bright", "lip", "blush", "sharpen")


def active(cfg: dict) -> bool:
    return bool(cfg) and any((cfg.get(k) or 0) > 0 for k in KEYS)


def suffix(cfg: dict) -> str:
    """hậu tố tên file (giống hệt beautySuffix() trong editor/logic.ts)"""
    if not active(cfg):
        return ""
    return "_b" + "-".join(str(int(cfg.get(k) or 0)) for k in KEYS) + "-" + (cfg.get("lipColor") or "C2185B").strip("#").upper() \
        + "-" + (cfg.get("blushColor") or "FF6F91").strip("#").upper()


def ensure_cv2():
    try:
        import cv2  # noqa
    except ImportError:
        print("Cài OpenCV (lần đầu)...")
        subprocess.run([sys.executable, "-m", "pip", "install", "opencv-python-headless"], check=False)


def _hex(c: str, default: str):
    c = (c or default).strip("#")
    try:
        return int(c[4:6], 16), int(c[2:4], 16), int(c[0:2], 16)  # BGR
    except Exception:
        return _hex(default, default)


class Beautifier:
    def __init__(self, cfg: dict):
        import cv2
        import numpy as np
        self.cv2, self.np = cv2, np
        self.cfg = {k: float(cfg.get(k) or 0) / 100.0 for k in KEYS}
        self.lip_bgr = np.array(_hex(cfg.get("lipColor"), "C2185B"), np.float32)
        self.blush_bgr = np.array(_hex(cfg.get("blushColor"), "FF6F91"), np.float32)
        self.det, self.yn = None, None
        yunet = ROOT / "models" / "face_detection_yunet_2023mar.onnx"
        if yunet.exists() and hasattr(cv2, "FaceDetectorYN"):  # ưu tiên YuNet (OpenCV 5 đã bỏ Haar)
            try:
                self.yn = cv2.FaceDetectorYN.create(str(yunet), "", (360, 640), 0.6, 0.3, 20)
            except Exception:
                self.yn = None
        if self.yn is None and hasattr(cv2, "CascadeClassifier"):
            path = CASCADE if CASCADE.exists() else Path(getattr(cv2, "data", None).haarcascades if hasattr(cv2, "data") else "") / "haarcascade_frontalface_default.xml"
            self.det = cv2.CascadeClassifier(str(path))
        self.face = None  # (x, y, w, h) đã làm mượt theo thời gian
        self.n = 0

    def _detect(self, img):
        cv2 = self.cv2
        h, w = img.shape[:2]
        s = 360.0 / w
        sm = cv2.resize(img, (360, int(h * s)))
        if self.yn is not None:
            self.yn.setInputSize((sm.shape[1], sm.shape[0]))
            r = self.yn.detect(sm)[1]
            fs = [tuple(float(v) for v in x[:4]) for x in r] if r is not None else []
        elif self.det is not None and not self.det.empty():
            fs = self.det.detectMultiScale(cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY), 1.1, 5, minSize=(40, 40))
        else:
            fs = []
        if len(fs):
            x, y, fw, fh = max(fs, key=lambda r: r[2] * r[3])
            box = (x / s, y / s, fw / s, fh / s)
            if self.face is None:
                self.face = box
            else:  # làm mượt để khỏi rung
                self.face = tuple(0.6 * a + 0.4 * b for a, b in zip(self.face, box))
            self.miss = 0
        else:
            self.miss = getattr(self, "miss", 0) + 1
            if self.miss > 15:
                self.face = None

    def track(self, img):
        """dò mặt (tuần tự, có làm mượt theo thời gian) -> khung mặt cho khung hình này"""
        if self.n % 3 == 0:
            self._detect(img)
        self.n += 1
        return self.face

    def __call__(self, img):
        """img: BGR uint8 -> BGR uint8 đã làm đẹp"""
        return self.apply(img, self.track(img))

    def apply(self, img, face):
        """phần nặng (chạy song song được): làm mịn, sáng da, son, má, độ nét"""
        cv2, np = self.cv2, self.np
        c = self.cfg
        out = img.astype(np.float32)
        h, w = img.shape[:2]
        # mặt nạ da (YCrCb), giới hạn quanh mặt/cổ nếu thấy mặt
        ycc = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
        skin = cv2.inRange(ycc, (40, 135, 85), (255, 180, 135)).astype(np.float32) / 255.0
        if face is not None:
            x, y, fw, fh = face
            area = np.zeros((h, w), np.float32)
            x0, x1 = int(max(0, x - fw * 0.6)), int(min(w, x + fw * 1.6))
            y0, y1 = int(max(0, y - fh * 0.5)), int(min(h, y + fh * 2.2))
            area[y0:y1, x0:x1] = 1.0
            area = cv2.GaussianBlur(area, (0, 0), fw * 0.15 + 1)
            skin *= np.maximum(area, 0.25)
        skin = cv2.GaussianBlur(skin, (0, 0), 4)
        m3 = skin[..., None]
        if c["smooth"] > 0:  # làm mịn: lọc giữ cạnh ở nửa độ phân giải, giữ lại chút chi tiết da
            half = cv2.resize(img, (w // 2, h // 2))
            sm = cv2.bilateralFilter(half, 0, 18 + 40 * c["smooth"], 5 + 4 * c["smooth"])
            sm = cv2.resize(sm, (w, h)).astype(np.float32)
            detail = out - cv2.GaussianBlur(out, (0, 0), 1.2)
            sm = sm + detail * (0.35 - 0.2 * c["smooth"])
            a = m3 * (0.95 * c["smooth"])
            out = out * (1 - a) + sm * a
        if c["bright"] > 0:  # sáng da: nâng sáng + bớt đỏ/xỉn nhẹ
            k = m3 * c["bright"]
            out = out + k * (255 - out) * 0.22
            gray = out.mean(axis=2, keepdims=True)
            out = out * (1 - k * 0.12) + gray * (k * 0.12)
        if face is not None and (c["lip"] > 0 or c["blush"] > 0):
            x, y, fw, fh = face
            if c["blush"] > 0:  # má hồng: 2 vệt mềm dưới mắt
                bl = np.zeros((h, w), np.float32)
                for cx in (x + fw * 0.28, x + fw * 0.72):
                    cv2.ellipse(bl, (int(cx), int(y + fh * 0.66)), (int(fw * 0.13), int(fh * 0.08)), 0, 0, 360, 1.0, -1)
                bl = cv2.GaussianBlur(bl, (0, 0), fw * 0.07 + 1) * skin
                k = (bl * 0.42 * c["blush"])[..., None]
                out = out * (1 - k) + (out * 0.5 + self.blush_bgr * 0.5) * k
            if c["lip"] > 0:  # son môi: vùng môi = đỏ hơn da xung quanh, trong khung miệng
                lx0, lx1 = int(x + fw * 0.28), int(x + fw * 0.72)
                ly0, ly1 = int(y + fh * 0.70), int(min(h, y + fh * 0.95))
                if lx1 > lx0 + 4 and ly1 > ly0 + 4:
                    reg = ycc[ly0:ly1, lx0:lx1].astype(np.float32)
                    cr = reg[..., 1]
                    ref = np.median(ycc[int(y + fh * 0.45):int(y + fh * 0.6), lx0:lx1, 1]) if fh > 20 else np.median(cr)
                    lm = np.clip((cr - ref - 3) / 10.0, 0, 1)
                    lm = cv2.GaussianBlur(lm, (0, 0), max(1.0, fw * 0.012))
                    lip = np.zeros((h, w), np.float32)
                    lip[ly0:ly1, lx0:lx1] = lm
                    k = (lip * 0.75 * c["lip"])[..., None]
                    lum = out.mean(axis=2, keepdims=True) / 160.0
                    tint = np.clip(self.lip_bgr * lum, 0, 255)
                    out = out * (1 - k) + tint * k
        if c["sharpen"] > 0:  # độ nét (cả khung)
            bl = cv2.GaussianBlur(out, (0, 0), 1.4)
            out = out + (out - bl) * (1.4 * c["sharpen"])
        return np.clip(out, 0, 255).astype(np.uint8)


def _probe(video: Path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-show_entries", "format=duration", "-of", "json", str(video)], capture_output=True, text=True)
    j = json.loads(r.stdout)
    return j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])


def preview(video: Path, t: float, cfg: dict, out: Path):
    """ảnh trước | sau ở giây t"""
    ensure_cv2()
    import cv2
    import numpy as np
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=-2:1280", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    img = cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError("Không đọc được khung hình")
    b = Beautifier(cfg)
    after = b(img)
    face = b.face
    if face is not None:  # thêm 1 hàng phóng to vùng mặt để dễ so
        x, y, fw, fh = [int(v) for v in face]
        pad = int(fw * 0.35)
        y0, y1, x0, x1 = max(0, y - pad), min(img.shape[0], y + fh + pad), max(0, x - pad), min(img.shape[1], x + fw + pad)
        zb, za = img[y0:y1, x0:x1], after[y0:y1, x0:x1]
        zh = img.shape[0] // 2
        zb = cv2.resize(zb, (int(zb.shape[1] * zh / zb.shape[0]), zh))
        za = cv2.resize(za, (zb.shape[1], zh))
        top = np.hstack([img, after])
        zoom = np.hstack([zb, za])
        zoom = cv2.resize(zoom, (top.shape[1], int(zoom.shape[0] * top.shape[1] / zoom.shape[1])))
        canvas = np.vstack([top, zoom])
    else:
        canvas = np.hstack([img, after])
    cv2.imwrite(str(out), canvas, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return {"face": face is not None}


def process(folder: Path, video_rel: str, cfg: dict, ranges: list = None, tick=None) -> str:
    """-> đường dẫn (tương đối dự án) video đã làm đẹp (dùng lại nếu đã có)."""
    folder = Path(folder)
    if not active(cfg):
        return video_rel
    src = folder / video_rel
    st = src.stat()
    rkey = json.dumps([[round(a, 1), round(b, 1)] for a, b in (ranges or [])])
    h = hashlib.md5(f"{video_rel}|{st.st_size}|{st.st_mtime}|{suffix(cfg)}|{rkey}".encode()).hexdigest()[:8]
    out = folder / "_work" / f"beauty_{h}.mp4"
    if out.exists():
        return out.relative_to(folder).as_posix()
    ensure_cv2()
    import numpy as np
    w, hh, dur = _probe(src)
    if hh > 1920:  # khung quá lớn: xử lý ở 1920 chiều cao (bộ dựng cũng chỉ cần chừng đó)
        w, hh = int(round(w * 1920 / hh / 2) * 2), 1920
    fps = 30
    n_all = int(dur * fps)
    keep = np.zeros(n_all + 2, bool)
    for a, b in (ranges or [[0, dur]]):
        keep[max(0, int((a - 0.5) * fps)):min(n_all + 2, int((b + 0.5) * fps) + 1)] = True
    print(f"Làm đẹp người: {keep.sum() / fps:.0f}s video cần xử lý...", flush=True)
    dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", str(src), "-vf", f"fps={fps},scale={w}:{hh}", "-f", "rawvideo",
                            "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    tmp = out.with_suffix(".tmp.mp4")
    from hw import cores, venc
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{hh}", "-r", str(fps),
                            "-i", "-", "-i", str(src), "-map", "0:v", "-map", "1:a?", *venc(), "-c:a", "copy", "-shortest", str(tmp)],
                           stdin=subprocess.PIPE)
    b = Beautifier(cfg)
    import cv2
    cv2.setNumThreads(1)  # song song theo khung hình thay vì trong từng phép lọc
    from concurrent.futures import ThreadPoolExecutor
    pool = ThreadPoolExecutor(max_workers=max(1, cores() - 1))
    fsz = w * hh * 3
    i = 0
    total = max(1, int(keep.sum()))
    done = 0
    batch = []  # (future hoặc bytes) giữ đúng thứ tự

    def flush(force=False):
        nonlocal done
        while batch and (force or len(batch) > cores() * 2):
            x = batch.pop(0)
            if isinstance(x, bytes):
                enc.stdin.write(x)
            else:
                enc.stdin.write(x.result().tobytes())
                done += 1
                if tick and done % 15 == 0:
                    tick(done / total)
    while True:
        buf = dec.stdout.read(fsz)
        if len(buf) < fsz:
            break
        if i < len(keep) and keep[i]:
            img = np.frombuffer(buf, np.uint8).reshape(hh, w, 3)
            batch.append(pool.submit(b.apply, img, b.track(img)))
        else:
            batch.append(buf)
        flush()
        i += 1
    flush(True)
    pool.shutdown()
    dec.stdout.close()
    dec.wait()
    enc.stdin.close()
    enc.wait()
    if enc.returncode or not tmp.exists():
        raise RuntimeError("Không ghi được video làm đẹp")
    tmp.replace(out)
    for old in (folder / "_work").glob("beauty_*.mp4"):  # bỏ bản làm đẹp cũ
        if old != out and ".tmp" not in old.name:
            old.unlink(missing_ok=True)
    return out.relative_to(folder).as_posix()


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    f = Path(sys.argv[1]).resolve()
    info = json.loads((f / "_work" / "info.json").read_text(encoding="utf-8"))
    plan = json.loads((f / "plan.json").read_text(encoding="utf-8"))
    cfg = plan.get("beauty") or {}
    if "--xem" in sys.argv:
        t = float(sys.argv[sys.argv.index("--xem") + 1])
        r = preview(f / info["video"], t, cfg or {"smooth": 50, "bright": 30}, f / "_work" / "beauty_xem.jpg")
        print("Ảnh trước/sau:", f / "_work" / "beauty_xem.jpg", "" if r["face"] else "(không thấy mặt — chỉ làm mịn/sáng theo màu da)")
    else:
        print("Xong:", process(f, info["video"], cfg, plan.get("segments")))
