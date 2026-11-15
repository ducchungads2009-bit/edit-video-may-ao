"""Tự dò BIỂN SỐ XE, MÃ QR, MÃ VẠCH trong video chính để CHE MỜ (tránh vi phạm chính sách TikTok / lộ thông tin).

  python scripts/nho_may.py chemo "<folder>"        (việc nặng — chạy trên máy thật qua giao diện)
  python scripts/che_mo.py "<folder>" [--fps 3] [--khong-ghi]

Cách làm: lấy 3 khung/giây của video chính (khung đầy đủ), dò
  - biển số: YOLOv9 "open-image-models" (giấy phép MIT, ONNX ~8 MB, tự tải lần đầu về models/) — chạy trên 2 nửa khung
    (trên / dưới, chồng nhau) để bắt cả biển số nhỏ;
  - mã QR + mã vạch: OpenCV (QRCodeDetectorAruco / BarcodeDetector).
Nối các lần thấy thành "vệt" theo thời gian (bám theo khi vật di chuyển), bỏ vệt chỉ thấy 1 lần mà độ tin thấp.
Kết quả: _work/che-mo.json + ghi vào plan.json trường "blurs" (giữ vùng người dùng tự thêm "kind": "tay" và vùng đã tắt / sửa):
  "blurs": [{"id": "p1", "kind": "bien-so" | "qr" | "ma-vach" | "tay", "mode": "blur" | "den", "off": false,
             "track": [[giây video gốc, x, y, w, h], ...]}]   (px theo khung video chính, giây TRƯỚC khi cắt đoạn)
EditPlan vẽ: khung đó của video được làm mờ mạnh (hoặc phủ khối đen), bám theo vệt, đi theo cả zoom / cắt đoạn.
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
MODEL = ROOT / "models" / "yolo-v9-t-640-license-plates-end2end.onnx"
MODEL_URL = "https://github.com/ankandrew/open-image-models/releases/download/assets/yolo-v9-t-640-license-plates-end2end.onnx"
GAP = 0.9      # giây: quá khoảng này không thấy nữa -> vệt kết thúc
PAD = 0.18     # nới hộp mỗi phía


def _model():
    if not MODEL.exists():
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        print("Tải bộ dò biển số (lần đầu, ~8 MB)...", flush=True)
        tmp = MODEL.with_suffix(".tmp")
        urllib.request.urlretrieve(MODEL_URL, tmp)
        tmp.replace(MODEL)
    import onnxruntime as ort
    return ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])


def _plates(sess, img, np, cv2, thr=0.45):
    """img BGR -> [(x, y, w, h, conf)] trên khung gốc; chạy trên 2 nửa chồng nhau"""
    H, W = img.shape[:2]
    out = []
    tiles = [(0, 0, W, H)] if H <= W * 1.2 else [(0, 0, W, int(H * 0.56)), (0, int(H * 0.44), W, H)]
    for (x0, y0, x1, y1) in tiles:
        crop = img[y0:y1, x0:x1]
        h, w = crop.shape[:2]
        r = min(640 / h, 640 / w)
        nw, nh = int(round(w * r)), int(round(h * r))
        im = cv2.resize(crop, (nw, nh))
        dw, dh = (640 - nw) / 2, (640 - nh) / 2
        im = cv2.copyMakeBorder(im, int(round(dh - 0.1)), int(round(dh + 0.1)), int(round(dw - 0.1)), int(round(dw + 0.1)), cv2.BORDER_CONSTANT, value=(114, 114, 114))
        t = im.transpose((2, 0, 1))[::-1][None].astype(np.float32) / 255.0
        try:
            pr = sess.run(None, {sess.get_inputs()[0].name: np.ascontiguousarray(t)})[0]
        except Exception:
            continue
        for row in np.asarray(pr).reshape(-1, 7):
            sc = float(row[6])
            if sc < thr:
                continue
            bx = [(row[1] - dw) / r + x0, (row[2] - dh) / r + y0, (row[3] - dw) / r + x0, (row[4] - dh) / r + y0]
            out.append((bx[0], bx[1], bx[2] - bx[0], bx[3] - bx[1], sc))
    return _nms(out)


def _iou(a, b):
    ax1, ay1, ax2, ay2 = a[0], a[1], a[0] + a[2], a[1] + a[3]
    bx1, by1, bx2, by2 = b[0], b[1], b[0] + b[2], b[1] + b[3]
    iw, ih = max(0, min(ax2, bx2) - max(ax1, bx1)), max(0, min(ay2, by2) - max(ay1, by1))
    i = iw * ih
    return i / max(1e-6, a[2] * a[3] + b[2] * b[3] - i)


def _nms(L, thr=0.4):
    L = sorted(L, key=lambda x: -x[4])
    keep = []
    for b in L:
        if all(_iou(b, k) < thr for k in keep):
            keep.append(b)
    return keep


def _codes(img, cv2, qr, bar):
    """mã QR + mã vạch -> [(x, y, w, h, conf, kind)]"""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    out = []
    for det, kind in ((qr, "qr"), (bar, "ma-vach")):
        if det is None:
            continue
        try:
            if kind == "qr":
                ok, pts = det.detectMulti(g)
            else:  # mã vạch: phải đọc ra được nội dung (máy dò mã vạch hay nhận nhầm sọc / chữ)
                r = det.detectAndDecode(g)  # khác nhau giữa các bản OpenCV: lấy mảng toạ độ + danh sách chữ đọc được
                pts = next((x for x in r if hasattr(x, "shape")), None)
                info = next((x for x in r if isinstance(x, (list, tuple)) or isinstance(x, str)), "")
                ok = pts is not None and any(bool(x) for x in (info if isinstance(info, (list, tuple)) else [info]))
                if ok:
                    keep = [i for i, x in enumerate(info if isinstance(info, (list, tuple)) else [info]) if x]
                    pts = [pts[i] for i in keep if i < len(pts)]
        except Exception:
            continue
        if not ok or pts is None:
            continue
        for p in pts:
            xs, ys = p[:, 0], p[:, 1]
            w, h = float(xs.max() - xs.min()), float(ys.max() - ys.min())
            if w < 12 or h < 8:
                continue
            out.append((float(xs.min()), float(ys.min()), w, h, 0.7, kind))  # < 0.75: phải thấy ≥ 2 lần mới che
    return out


def detect(video: Path, fps: float = 3.0, log=print):
    from beauty import ensure_cv2
    ensure_cv2()
    import cv2
    import numpy as np
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                         "-of", "json", str(video)], capture_output=True, text=True)
    meta = json.loads(pr.stdout or "{}")
    W, H = meta["streams"][0]["width"], meta["streams"][0]["height"]
    dur = float(meta.get("format", {}).get("duration") or 0)
    try:
        sess = _model()
    except Exception as e:  # không tải được -> vẫn dò mã QR
        sess = None
        log(f"[!] Không tải được bộ dò biển số ({e}) — chỉ dò mã QR / mã vạch.")
    qr = cv2.QRCodeDetectorAruco() if hasattr(cv2, "QRCodeDetectorAruco") else (cv2.QRCodeDetector() if hasattr(cv2, "QRCodeDetector") else None)
    bar = cv2.barcode.BarcodeDetector() if hasattr(cv2, "barcode") else None
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", str(video), "-vf", f"fps={fps}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         stdout=subprocess.PIPE)
    n = W * H * 3
    hits = []  # (t, x, y, w, h, conf, kind)
    k = 0
    try:
        from tiendo import Tien
        tien = Tien(Path(sys.argv[1]).resolve(), "chemo", dur) if len(sys.argv) > 1 else None
    except Exception:
        tien = None
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        t = k / fps
        if sess is not None:
            for (x, y, w, h, c) in _plates(sess, img, np, cv2):
                if w > 10 and h > 5:
                    hits.append((t, x, y, w, h, c, "bien-so"))
        for (x, y, w, h, c, kd) in _codes(img, cv2, qr, bar):
            hits.append((t, x, y, w, h, c, kd))
        k += 1
        if tien and k % 6 == 0:
            tien.update(min(0.98, t / max(1, dur)), f"Dò biển số / mã QR {int(t)}/{int(dur)} giây")
    p.wait()
    if tien:
        tien.done(True)
    return hits, W, H


def link(hits, W, H):
    """nối các lần thấy thành vệt; trả [{"kind", "conf", "track": [[t, x, y, w, h]]}]"""
    tracks = []
    for (t, x, y, w, h, c, kd) in sorted(hits):
        best, bs = None, 0.0
        for tr in tracks:
            if tr["kind"] != kd or t - tr["track"][-1][0] > GAP or t == tr["track"][-1][0]:
                continue
            lt = tr["track"][-1]
            s = _iou((x, y, w, h), lt[1:5])
            dc = ((x + w / 2 - lt[1] - lt[3] / 2) ** 2 + (y + h / 2 - lt[2] - lt[4] / 2) ** 2) ** 0.5
            if dc < max(w, h, lt[3], lt[4]) * 1.2:
                s = max(s, 0.25)
            if s > bs:
                best, bs = tr, s
        if best and bs >= 0.15:
            best["track"].append([t, x, y, w, h])
            best["conf"] = max(best["conf"], c)
            best["n"] += 1
        else:
            tracks.append({"kind": kd, "conf": c, "n": 1, "track": [[t, x, y, w, h]]})
    out = []
    for tr in tracks:
        if tr["n"] < 2 and tr["conf"] < 0.75:
            continue  # chỉ thấy 1 lần, không chắc -> bỏ (tránh che nhầm)
        pts = tr["track"]
        res = []
        for i, (t, x, y, w, h) in enumerate(pts):
            # cỡ hộp làm mượt (trung bình 3 lần thấy); vị trí giữ nguyên (làm mượt vị trí làm hộp trễ sau vật đang chạy)
            win = pts[max(0, i - 1): i + 2]
            sw, sh = sum(v[3] for v in win) / len(win), sum(v[4] for v in win) / len(win)
            cx, cy = x + w / 2, y + h / 2
            # vật di chuyển nhanh -> nới thêm theo quãng đường tới lần thấy kề bên (giữa 2 lần lấy mẫu vẫn phủ kín)
            mv = [abs((q[1] + q[3] / 2) - cx) for q in win] + [0]
            mh = [abs((q[2] + q[4] / 2) - cy) for q in win] + [0]
            px, py = sw * PAD + max(mv) * 0.35, sh * (PAD + 0.1) + max(mh) * 0.35
            x0, y0 = max(0, cx - sw / 2 - px), max(0, cy - sh / 2 - py)
            x1, y1 = min(W, cx + sw / 2 + px), min(H, cy + sh / 2 + py)
            res.append([round(t, 2), round(x0), round(y0), round(x1 - x0), round(y1 - y0)])
        out.append({"kind": tr["kind"], "conf": round(tr["conf"], 2), "track": res})
    return out


NAME = {"bien-so": "biển số", "qr": "mã QR", "ma-vach": "mã vạch"}


def merge_plan(folder: Path, tracks: list) -> int:
    pf = folder / "plan.json"
    if not pf.exists():
        return 0
    plan = json.loads(pf.read_text(encoding="utf-8"))
    old = plan.get("blurs") or []
    keep = [b for b in old if b.get("kind") == "tay" or b.get("sua")]
    offs = {b.get("id") for b in old if b.get("off") and b.get("kind") != "tay"}
    cnt = {}
    new = []
    for tr in tracks:
        cnt[tr["kind"]] = cnt.get(tr["kind"], 0) + 1
        bid = {"bien-so": "p", "qr": "q", "ma-vach": "b"}[tr["kind"]] + str(cnt[tr["kind"]])
        b = {"id": bid, "kind": tr["kind"], "mode": "blur", "track": tr["track"]}
        if bid in offs:
            b["off"] = True
        new.append(b)
    plan["blurs"] = keep + new
    pf.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(new)


def run(folder: Path, fps: float = 3.0, write_plan: bool = True):
    info = json.loads((folder / "_work" / "info.json").read_text(encoding="utf-8"))
    video = folder / info["video"]
    if info.get("mode") == "voice" and (folder / "_work" / "edit.mp4").exists():
        video = folder / "_work" / "edit.mp4"  # chế độ VOICE: video chính = cảnh đã ghép theo voice
    hits, W, H = detect(video, fps)
    tracks = link(hits, W, H)
    (folder / "_work" / "che-mo.json").write_text(json.dumps({"w": W, "h": H, "fps": fps, "tracks": tracks}, ensure_ascii=False), encoding="utf-8")
    n = merge_plan(folder, tracks) if write_plan else 0
    return tracks, n


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    f = Path(sys.argv[1]).resolve()
    fps = float(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 3.0
    tracks, n = run(f, fps, "--khong-ghi" not in sys.argv)
    if not tracks:
        print("Không thấy biển số / mã QR / mã vạch nào cần che.")
    for tr in tracks:
        a, b = tr["track"][0][0], tr["track"][-1][0]
        print(f"- {NAME[tr['kind']]}: {a:.1f}–{b:.1f}s (giây video gốc), độ tin {tr['conf']}, {len(tr['track'])} lần thấy")
    print(f"Kết quả: {f / '_work' / 'che-mo.json'}" + (f" · đã ghi {n} vùng che vào plan.json (\"blurs\")" if n else ""))
