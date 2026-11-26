"""Dò BÀN TAY người nói trong video chính (MediaPipe Hand Landmarker, chạy offline) -> đầu ngón trỏ theo thời gian + cử chỉ VUỐT.
Dùng cho khối màn hình 3D (screen3d): màn hình nghiêng theo tay, loé sáng chỗ chạm, chuyển trang khi vuốt.

  python scripts/tay.py "<folder>"                      # cả video -> _work/tay.json
  python scripts/tay.py "<folder>" --khoi 5             # chỉ khoảng thời gian của khối số 5 trong plan.json, ghi handPts + swipes vào khối
  python scripts/tay.py "<folder>" --tu 12.5 --den 20   # khoảng giây (video gốc)

Kết quả _work/tay.json: {"step": 1/15, "pts": [[t, x, y, cx, cy, cỡ]], "swipes": [[t, hướng]]} — t = giây VIDEO GỐC (trước khi cắt
đoạn), x, y = đầu ngón trỏ, cx, cy = tâm bàn tay, cỡ = bề rộng bàn tay (px trên khung 1080x1920); hướng +1 = vuốt sang trái (lật trang tiếp), -1 = vuốt sang phải (trang trước).
Mô hình: models/hand_landmarker.task (tự tải lần đầu ~7MB từ Google). Thiếu thư viện -> tự cài mediapipe.
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
MODEL = ROOT / "models" / "hand_landmarker.task"
URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
FPS = 15
SW, SH = 540, 960


def ensure():
    try:
        import mediapipe  # noqa: F401
    except Exception:
        print("Cài thư viện dò tay (mediapipe, 1 lần)...", flush=True)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "mediapipe"])
    if not MODEL.exists():
        print("Tải mô hình dò tay (~7MB, 1 lần)...", flush=True)
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        tmp = MODEL.with_suffix(".tmp")
        urllib.request.urlretrieve(URL, tmp)
        tmp.replace(MODEL)


def detect(video: Path, t0: float, t1: float):
    import mediapipe as mp
    import numpy as np
    from mediapipe.tasks.python import BaseOptions, vision
    lm = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL)), num_hands=2, running_mode=vision.RunningMode.VIDEO,
        min_hand_detection_confidence=0.4, min_hand_presence_confidence=0.4, min_tracking_confidence=0.4))
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{t0:.3f}", "-t", f"{max(0.1, t1 - t0):.3f}", "-i", str(video),
                          "-vf", f"fps={FPS},scale={SW}:{SH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = SW * SH * 3
    k, raw = 0, []
    prev = None
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        img = np.ascontiguousarray(np.frombuffer(buf, np.uint8).reshape(SH, SW, 3))
        r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=img), int(k * 1000 / FPS))
        t = t0 + k / FPS
        if r.hand_landmarks:
            # nhiều tay: chọn tay giơ cao nhất (đang chỉ / vuốt), ưu tiên tay gần vị trí trước đó
            cand = []
            for h in r.hand_landmarks:
                xs, ys = [q.x * 1080 for q in h], [q.y * 1920 for q in h]
                cand.append((h[8].x * 1080, h[8].y * 1920, sum(xs) / 21, sum(ys) / 21, max(max(xs) - min(xs), max(ys) - min(ys))))
            if prev:
                cand.sort(key=lambda c: (c[1] - prev[1] * 0) + 0.6 * ((c[0] - prev[0]) ** 2 + (c[1] - prev[1]) ** 2) ** 0.5)
            else:
                cand.sort(key=lambda c: c[1])
            x, y, hx, hy, hs = cand[0]
            if y < 1900:  # bỏ tay sát mép dưới (đang để trên bàn)
                raw.append([round(t, 3), x, y, hx, hy, hs])
                prev = (x, y)
        k += 1
    p.wait()
    try:
        lm.close()
    except Exception:
        pass
    return raw


def smooth(raw):
    """làm mượt (trung bình 5 mẫu trong cùng 1 đoạn liền) để màn hình không rung"""
    out = []
    for i, q0 in enumerate(raw):
        t = q0[0]
        win = [q for q in raw[max(0, i - 2):i + 3] if abs(q[0] - t) <= 2.5 / FPS]
        out.append([t, *[round(sum(q[k] for q in win) / len(win), 1) for k in range(1, len(q0))]])
    return out


def swipes(pts, minv=1100, mind=170, gap=0.6):
    """vuốt = đầu ngón tay đi ngang nhanh (> minv px/giây) và đủ xa (> mind px) trong ~0.35 giây"""
    res, last = [], -9
    for i, q in enumerate(pts):
        t, x, y = q[0], q[1], q[2]
        j = i
        while j + 1 < len(pts) and pts[j + 1][0] - t <= 0.35 and pts[j + 1][0] - pts[j][0] < 0.2:
            j += 1
        if j == i:
            continue
        dx = pts[j][1] - x
        dy = pts[j][2] - y
        dt = pts[j][0] - t
        if abs(dx) > mind and abs(dx) / dt > minv and abs(dx) > abs(dy) * 1.3 and t - last > gap:
            res.append([round(t + dt / 2, 2), 1 if dx < 0 else -1])
            last = t
    return res


def o2s(segs, t):
    if not segs:
        return t
    acc = 0
    for a, b in segs:
        if t < acc + (b - a):
            return a + (t - acc)
        acc += b - a
    return segs[-1][1]


def compute(folder: Path, plan: dict, i: int):
    """cho trình chỉnh sửa (plan chưa lưu): dò tay trong khoảng của khối i -> (handPts, swipes)"""
    info = json.loads((folder / "_work" / "info.json").read_text(encoding="utf-8"))
    e = plan["elements"][i]
    dur = float(info["durationSec"])
    t0, t1 = max(0, o2s(plan.get("segments"), e["start"]) - 0.3), min(dur, o2s(plan.get("segments"), e["end"]) + 0.3)
    ensure()
    pts = smooth(detect(folder / info["video"], t0, t1))
    return [[round(q[0], 2), *[round(v) for v in q[1:]]] for q in pts], swipes(pts)


def run(folder: Path, khoi=None, tu=None, den=None):
    work = folder / "_work"
    info = json.loads((work / "info.json").read_text(encoding="utf-8"))
    video = folder / info["video"]
    dur = float(info["durationSec"])
    plan_p = folder / "plan.json"
    t0, t1 = tu or 0.0, den or dur
    if khoi is not None:
        plan = json.loads(plan_p.read_text(encoding="utf-8"))
        e = plan["elements"][khoi]
        segs = plan.get("segments")
        t0, t1 = max(0, o2s(segs, e["start"]) - 0.3), min(dur, o2s(segs, e["end"]) + 0.3)
    ensure()
    print(f"Dò tay {t0:.1f}–{t1:.1f}s ...", flush=True)
    pts = smooth(detect(video, t0, t1))
    sw = swipes(pts)
    (work / "tay.json").write_text(json.dumps({"step": round(1 / FPS, 4), "w": 1080, "h": 1920, "pts": pts, "swipes": sw}), encoding="utf-8")
    print(f"Thấy tay ở {len(pts)} mẫu, {len(sw)} lần vuốt: " + ", ".join(f"{t}s {'←' if d > 0 else '→'}" for t, d in sw))
    if khoi is not None:
        plan = json.loads(plan_p.read_text(encoding="utf-8"))
        e = plan["elements"][khoi]
        e["handPts"] = [[round(q[0], 2), *[round(v) for v in q[1:]]] for q in pts]
        e["swipes"] = sw
        plan_p.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Đã ghi handPts + swipes vào khối {khoi} ({e.get('type')})")
    return pts, sw


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()

    def opt(k, cast=float):
        return cast(a[a.index(k) + 1]) if k in a and a.index(k) + 1 < len(a) else None
    run(Path(a[0]).resolve(), opt("--khoi", int), opt("--tu"), opt("--den"))
