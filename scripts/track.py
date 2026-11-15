"""BÁM VẬT THỂ (motion tracking, giống Tracker của AE) — offline, chỉ cần opencv.
Bám 1 điểm trên video chính (vd cái bàn, cửa sổ, tay người) bằng optical flow Lucas–Kanade nhiều điểm đặc trưng quanh đó
(lấy trung vị, kiểm tra xuôi–ngược, tự dò lại điểm khi mất), làm mượt, rồi ghi vào khối: "trackPts": [[giây gốc, x, y], ...].
Khối có trackPts sẽ dời theo vật (EditPlan.tsx FxWrap) — nhãn chữ, mũi tên, khung, nhãn dán… dính vào vật.

  python scripts/track.py "<folder>" <số thứ tự khối> [--x 540 --y 900] [--r 60]
     --x/--y: điểm cần bám (px trên khung 1080x1920 ở lúc khối bắt đầu); bỏ trống = tâm khối ước lượng (shape: x,y; sticker: x,y)
     --r: bán kính vùng lấy điểm đặc trưng (px, mặc định 60)
  python scripts/track.py "<folder>" <số> --xoa      # bỏ bám
Chỉ bám trong đoạn video gốc chứa lúc khối bắt đầu (qua điểm nối thì giữ nguyên vị trí cuối).
"""
import json
import sys
from pathlib import Path

W, H = 1080, 1920


def out2src(segs, t):
    if not segs:
        return t, None
    acc = 0.0
    for a, b in segs:
        if t < acc + (b - a):
            return a + (t - acc), (a, b)
        acc += b - a
    a, b = segs[-1]
    return b, (a, b)


def anchor_of(e):
    """điểm mặc định để bám: tâm khối (px)"""
    ty = e.get("type")
    x, y = e.get("x"), e.get("y")
    fx = lambda v, full, d: d if v is None else (v * full if abs(v) <= 1 and v != 0 else v)  # noqa: E731
    if ty == "shape":
        if (e.get("kind") or "arrow") in ("arrow", "line"):  # mũi tên: bám đầu mũi tên (chỗ nó chỉ vào)
            x0, y0 = fx(x, W, 540), fx(y, H, 900)
            return fx(e.get("x2"), W, x0 + 260), fx(e.get("y2"), H, y0 - 200)
        return fx(x, W, 540), fx(y, H, 900)
    if ty in ("sticker",):
        s = e.get("size") or 150
        return fx(x, W, 540), (y if y is not None else 600) + s / 2
    if ty == "text":
        return fx(x, W, 540), (y if y is not None else 700) + (e.get("size") or 80) * 0.6
    return fx(x, W, 540), fx(y, H, 900)


def track(video: str, t0: float, t1: float, x: float, y: float, r: int = 60, step: int = 1):
    import cv2
    import numpy as np
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    vw, vh = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    sx, sy = vw / W, vh / H  # khung video -> khung 1080x1920
    cap.set(cv2.CAP_PROP_POS_MSEC, t0 * 1000)
    ok, fr = cap.read()
    if not ok:
        return []
    scale = 540 / max(vw, 1)  # bám trên ảnh nhỏ cho nhanh (rộng 540)
    small = lambda im: cv2.cvtColor(cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)  # noqa: E731
    g0 = small(fr)
    px, py = x * sx * scale, y * sy * scale
    rr = max(12, r * sx * scale)

    def detect(g, cx, cy):
        m = np.zeros_like(g)
        cv2.circle(m, (int(cx), int(cy)), int(rr), 255, -1)
        p = cv2.goodFeaturesToTrack(g, maxCorners=40, qualityLevel=0.01, minDistance=3, mask=m, blockSize=5)
        return p if p is not None else np.empty((0, 1, 2), np.float32)

    pts = detect(g0, px, py)
    lk = dict(winSize=(21, 21), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    out = [[round(t0, 3), x, y]]
    n = int((t1 - t0) * fps)
    t = t0
    for k in range(1, n + 1):
        ok, fr = cap.read()
        if not ok:
            break
        t = t0 + k / fps
        g1 = small(fr)
        if len(pts) >= 3:
            p1, st, _ = cv2.calcOpticalFlowPyrLK(g0, g1, pts, None, **lk)
            p0r, st2, _ = cv2.calcOpticalFlowPyrLK(g1, g0, p1, None, **lk)
            fb = np.linalg.norm((pts - p0r).reshape(-1, 2), axis=1)
            good = (st.reshape(-1) == 1) & (st2.reshape(-1) == 1) & (fb < 1.5)
            if good.sum() >= 3:
                d = (p1 - pts).reshape(-1, 2)[good]
                px += float(np.median(d[:, 0]))
                py += float(np.median(d[:, 1]))
                pts = p1[good].reshape(-1, 1, 2)
            else:
                pts = np.empty((0, 1, 2), np.float32)
        if len(pts) < 8:  # mất nhiều điểm -> dò lại quanh vị trí hiện tại
            pts = detect(g1, px, py)
        g0 = g1
        if k % step == 0:
            out.append([round(t, 3), px / scale / sx, py / scale / sy])
    cap.release()
    # làm mượt (trung bình trượt 5 mẫu), giữ điểm đầu đúng chỗ
    if len(out) > 5:
        xs = np.array([o[1] for o in out]), np.array([o[2] for o in out])
        ker = np.ones(5) / 5
        sm = [np.convolve(np.pad(a, 2, mode="edge"), ker, mode="valid") for a in xs]
        dx0, dy0 = sm[0][0] - out[0][1], sm[1][0] - out[0][2]
        out = [[o[0], round(float(sm[0][i] - dx0), 1), round(float(sm[1][i] - dy0), 1)] for i, o in enumerate(out)]
    # thưa bớt: 1 mẫu / 2 khung
    return out[::2] + ([out[-1]] if len(out) % 2 == 0 else [])


def compute(folder: Path, plan: dict, idx: int, x=None, y=None, r=60):
    """tính trackPts cho khối idx của plan (không ghi file)"""
    els = plan.get("elements") or []
    if not (0 <= idx < len(els)) or not els[idx]:
        raise SystemExit(f"Không có khối #{idx}")
    e = els[idx]
    info = json.loads((folder / "_work" / "info.json").read_text(encoding="utf-8"))
    video = folder / info.get("video", "")
    if not video.is_file():
        raise SystemExit("Không thấy video chính (_work/info.json) — chạy prepare trước")
    segs = [s for s in plan.get("segments") or [] if s[1] - s[0] > 0.05]
    s0, seg = out2src(segs, float(e["start"]))
    s1 = s0 + (e["end"] - e["start"])
    if seg:
        s1 = min(seg[1], s1)
    if x is None or y is None:
        ax, ay = anchor_of(e)
        x = ax + (e.get("dx") or 0) if x is None else x
        y = ay + (e.get("dy") or 0) if y is None else y
    pts = track(str(video), s0, s1, float(x), float(y), r)
    if len(pts) < 2:
        raise SystemExit("Không bám được (video quá tối / trơn, hoặc ngoài thời lượng)")
    return pts


def run(folder: Path, idx: int, x=None, y=None, r=60, clear=False):
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    els = plan.get("elements") or []
    if not (0 <= idx < len(els)) or not els[idx]:
        raise SystemExit(f"Không có khối #{idx}")
    e = els[idx]
    if clear:
        e.pop("trackPts", None)
        (folder / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Đã bỏ bám vật thể ở khối #{idx}.")
        return []
    pts = compute(folder, plan, idx, x, y, r)
    s0, s1 = pts[0][0], pts[-1][0]
    e["trackPts"] = pts
    (folder / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    mx = max(abs(p[1] - pts[0][1]) + abs(p[2] - pts[0][2]) for p in pts)
    print(f"Đã bám vật thể cho khối #{idx} ({e.get('type')}): {len(pts)} mẫu, {s0:.2f}–{s1:.2f}s gốc, dịch tối đa ~{mx:.0f}px.")
    return pts


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    f = Path(a[0]).resolve()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from tiendo import stop_guard
        stop_guard(f)
    except ImportError:
        pass

    def opt(k, cast=float):
        return cast(a[a.index(k) + 1]) if k in a else None

    run(f, int(a[1]), opt("--x"), opt("--y"), opt("--r", int) or 60, "--xoa" in a)
