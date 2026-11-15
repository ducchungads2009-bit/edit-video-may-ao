"""ẢNH TĨNH -> VIDEO 2.5D (parallax, giống hiệu ứng "3D photo" / Depth của AE).
Ước lượng ĐỘ SÂU của ảnh (mô hình Depth Anything V2 small, ONNX, chạy offline — tự tải ~27MB lần đầu vào models/),
rồi dời từng điểm ảnh theo độ sâu khi camera chuyển động: vật gần trôi nhanh, nền xa trôi chậm -> cảm giác 3D.
Không tải được mô hình thì dùng độ sâu ước lượng (người/tiền cảnh gần — mô hình tách người có sẵn — + dưới gần trên xa).

  python scripts/parallax.py "<folder>" "<ảnh trong dự án>" [--move dolly|pan|orbit|rise|zoomout] [--dur 4] [--amount 1]
  -> assets/_xu-ly/<tên>_parallax_<move>.mp4 (1080x1920, 30fps) — dùng làm "src" của broll / card3d / pip
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "models" / "depth_anything_v2_small_q.onnx"
MODEL_URLS = [
    "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model_quantized.onnx",
    "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx",
]
W, H, FPS = 1080, 1920, 30


def ensure_model() -> bool:
    if MODEL.exists() and MODEL.stat().st_size > 1_000_000:
        return True
    import urllib.request
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    for u in MODEL_URLS:
        try:
            print("Tải mô hình độ sâu (lần đầu)...")
            tmp = MODEL.with_suffix(".tmp")
            urllib.request.urlretrieve(u, tmp)
            if tmp.stat().st_size > 1_000_000:
                tmp.replace(MODEL)
                return True
        except Exception as ex:  # noqa: BLE001
            print(f"  không tải được ({type(ex).__name__}) — thử nguồn khác")
    return False


def cover(img, w=W, h=H, extra=1.0):
    import cv2
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih) * extra
    r = cv2.resize(img, (int(iw * s + 0.5), int(ih * s + 0.5)), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    y0, x0 = (r.shape[0] - h) // 2, (r.shape[1] - w) // 2
    return r[y0:y0 + h, x0:x0 + w]


def depth_model(img):
    import cv2
    import numpy as np
    import onnxruntime as ort
    sess = ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    sz = 518
    x = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), (sz, sz), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    d = sess.run(None, {inp.name: x})[0]
    d = np.squeeze(d).astype(np.float32)
    d = cv2.resize(d, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_CUBIC)
    d = (d - d.min()) / (d.max() - d.min() + 1e-6)  # lớn = gần
    return d


def depth_heuristic(img):
    """không có mô hình: dưới gần, trên xa + người (mô hình tách người RVM nếu có) + vùng nét/tương phản cao gần hơn"""
    import cv2
    import numpy as np
    h, w = img.shape[:2]
    d = np.tile(np.linspace(0.15, 0.75, h, dtype=np.float32)[:, None], (1, w))
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    sharp = cv2.GaussianBlur(np.abs(cv2.Laplacian(g, cv2.CV_32F)), (0, 0), 25)
    sharp /= sharp.max() + 1e-6
    d = 0.75 * d + 0.25 * sharp
    rvm = ROOT / "models" / "rvm_mobilenetv3_fp32.onnx"
    try:
        if rvm.exists():
            import onnxruntime as ort
            s = ort.InferenceSession(str(rvm), providers=["CPUExecutionProvider"])
            src = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32).transpose(2, 0, 1)[None] / 255
            rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4
            outs = s.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                "downsample_ratio": np.array([0.25], np.float32)})
            pha = np.squeeze(outs[1]).astype(np.float32)
            d = np.maximum(d, pha * 0.95)
    except Exception:  # noqa: BLE001
        pass
    return d


def make(folder: Path, src: str, move="dolly", dur=4.0, amount=1.0) -> Path:
    import cv2
    import numpy as np
    sp = (folder / src).resolve()
    img = cv2.imread(str(sp), cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"Không đọc được ảnh: {src}")
    E = 1.18  # phóng sẵn để dời không lộ mép
    base = cover(img, W, H, E)
    work = cv2.resize(base, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    d = None
    if ensure_model():
        try:
            d = depth_model(work)
        except Exception as ex:  # noqa: BLE001
            print(f"Mô hình độ sâu lỗi ({ex}) — dùng độ sâu ước lượng")
    if d is None:
        d = depth_heuristic(work)
    d = cv2.resize(d, (W, H), interpolation=cv2.INTER_LINEAR)
    # giữ mép tiền cảnh gọn (giãn vùng gần) rồi làm mềm
    d = cv2.dilate(d, np.ones((9, 9), np.uint8))
    d = cv2.GaussianBlur(d, (0, 0), 6)
    out = folder / "assets" / "_xu-ly" / f"{sp.stem}_parallax_{move}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H * 0.45
    n = max(2, int(dur * FPS))
    A = float(amount)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
                          stdin=subprocess.PIPE)
    dn = (d - 0.5).astype(np.float32)  # -0.5 xa .. +0.5 gần
    for i in range(n):
        t = i / (n - 1)
        k = t * t * (3 - 2 * t)  # êm đầu cuối
        mx = my = 0.0
        zs = 1.0
        if move == "dolly":  # camera tiến vào: gần phóng nhiều hơn xa
            zs = 1 + 0.10 * A * k
            par = 0.09 * A * k
        elif move == "zoomout":
            zs = 1.10 - 0.10 * A * k
            par = 0.09 * A * (1 - k)
        else:
            par = 0
        if move == "pan":
            mx = (k - 0.5) * 70 * A
        elif move == "orbit":
            mx = np.sin((k - 0.5) * np.pi) * 60 * A
            my = -np.cos(k * np.pi) * 14 * A
            zs = 1 + 0.04 * A * np.sin(k * np.pi)
        elif move == "rise":
            my = (0.5 - k) * 70 * A
            zs = 1 + 0.03 * A * k
        # toạ độ nguồn: phóng quanh tâm theo độ sâu + trượt ngang/dọc tỉ lệ độ sâu
        s = zs * (1 + par * dn)
        mapx = cx + (xx - cx) / s - mx * dn * 2
        mapy = cy + (yy - cy) / s - my * dn * 2
        fr = cv2.remap(base, mapx.astype(np.float32), mapy.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        ff.stdin.write(fr.tobytes())
    ff.stdin.close()
    ff.wait()
    if not out.exists():
        raise SystemExit("ffmpeg lỗi khi ghi video parallax")
    print(f"Đã tạo video 2.5D: {out.relative_to(folder).as_posix()} ({dur:.1f}s, {move})")
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)

    def opt(k, d, cast=str):
        return cast(a[a.index(k) + 1]) if k in a else d

    f = Path(a[0]).resolve()
    o = make(f, a[1], opt("--move", "dolly"), opt("--dur", 4.0, float), opt("--amount", 1.0, float))
    print(json.dumps({"path": o.relative_to(f).as_posix()}, ensure_ascii=False))
