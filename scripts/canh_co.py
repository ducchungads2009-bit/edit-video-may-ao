"""Tự đổi CỠ CẢNH video chính kiểu toàn – trung – cận (như quay nhiều máy), cắt thẳng ở chỗ ngắt câu — thay cho zoom.

    python scripts/canh_co.py "<folder>" [--thua|--day] [--bo]

Ghi plan.json "shots": [{"t": giây trong video gốc, "s": cỡ, "x": tâm ngang 0–1, "y": tâm dọc 0–1, "k": "toan|trung|can"}].
Khung đổi đột ngột (cắt) đúng lúc ngắt câu, phóng quanh MẶT người nói (_work/mat.json) nên không bao giờ lộ mép.
"shots": [] = người dùng đã tắt -> không tự tạo lại.
"""
import json
import sys
from pathlib import Path

LEVELS = {"toan": 1.0, "trung": 1.28, "can": 1.6}
# vòng đổi cỡ: không lặp cỡ liền nhau, cận không đứng cạnh toàn quá thường xuyên
CYCLE = ["toan", "trung", "toan", "can", "trung", "toan"]  # quay về toàn thường xuyên, cận ít
DENS = {"thua": (14.0,), "vua": (9.0,), "day": (6.0,)}  # cảnh dài tối thiểu (giây) — đổi cỡ ít thôi, đổi nhiều xem rất mệt


def bounds(words: list) -> list:
    """mọi chỗ giữa 2 chữ: (giây gốc, độ "ngắt" = khoảng lặng, cộng thêm nếu có dấu câu)"""
    out = []
    for a, b in zip(words, words[1:]):
        w = str(a.get("w", ""))
        g = max(0.0, b["start"] - a["end"]) + (0.5 if w[-1:] in ".,!?;:…" else 0)
        out.append((round((a["end"] + b["start"]) / 2, 2), g))
    return out


def pick_cuts(bs: list, start: float, lo: float) -> list:
    """chọn mốc cắt: mỗi cảnh dài ≥ lo; trong cửa sổ [lo, 1.8·lo] lấy chỗ ngắt rõ nhất (lặng lâu nhất / có dấu câu)"""
    cuts, last = [start], start
    i = 0
    while True:
        win = [(t, g) for t, g in bs if last + lo <= t <= last + lo * 1.5]
        if not win:
            nxt = [(t, g) for t, g in bs if t > last + lo * 1.5]
            if not nxt:
                break
            win = nxt[:1]
        t = max(win, key=lambda x: x[1])[0]
        cuts.append(t)
        last = t
        i += 1
        if i > 2000:
            break
    return cuts


def face_at(m: dict, t0: float, t1: float):
    """tâm mặt trung bình trong khoảng [t0, t1] -> (x, y) tỉ lệ 0–1; không có mặt -> None"""
    if not m or not m.get("faces"):
        return None
    W, H = m.get("w", 1080), m.get("h", 1920)
    pts = [(f[1] + f[3] / 2, f[2] + f[4] / 2) for f in m["faces"] if len(f) >= 5 and t0 - 0.25 <= f[0] <= t1 + 0.25]
    if not pts:
        return None
    pts.sort()
    x, y = pts[len(pts) // 2]  # trung vị cho khỏi giật vì 1 mẫu sai
    return round(min(0.92, max(0.08, x / W)), 3), round(min(0.9, max(0.1, y / H)), 3)


def make(words: list, mat: dict, dur: float, density: str = "vua", segments=None) -> list:
    lo = DENS.get(density, DENS["vua"])[0]
    bs = bounds(words)
    # chỉ giữ mốc nằm trong đoạn được giữ lại (nếu có segments)
    if segments:
        bs = [b for b in bs if any(a + 0.4 <= b[0] <= e - 0.4 for a, e in segments)]
        start = segments[0][0]
    else:
        start = 0.0
    cuts = pick_cuts(bs, start, lo)
    end = segments[-1][1] if segments else dur
    cuts = [c for c in cuts if c == start or end - c >= 4.0]  # không đổi cảnh sát cuối video
    shots = []
    for i, t in enumerate(cuts):
        t1 = cuts[i + 1] if i + 1 < len(cuts) else dur
        k = CYCLE[i % len(CYCLE)]
        f = face_at(mat, t, t1)
        if not f and k != "toan":
            k = "toan"  # không thấy mặt (quay cảnh / màn hình) -> giữ cảnh toàn
        x, y = f or (0.5, 0.45)
        if shots and shots[-1]["k"] == k:
            continue
        shots.append({"t": round(t, 2), "s": LEVELS[k], "x": x, "y": y, "k": k})
    return shots


def run(folder: Path, density: str = "vua", plan: dict = None) -> dict:
    work = folder / "_work"
    words = json.loads((work / "words.json").read_text(encoding="utf-8")) if (work / "words.json").exists() else []
    mat = json.loads((work / "mat.json").read_text(encoding="utf-8")) if (work / "mat.json").exists() else {}
    info = json.loads((work / "info.json").read_text(encoding="utf-8")) if (work / "info.json").exists() else {}
    plan = plan if plan is not None else json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    plan["shots"] = make(words, mat, info.get("durationSec") or (words[-1]["end"] if words else 0), density, plan.get("segments"))
    return plan


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    f = Path(sys.argv[1])
    pj = f / "plan.json"
    p = json.loads(pj.read_text(encoding="utf-8"))
    if "--bo" in sys.argv:
        p["shots"] = []
        print("Đã tắt đổi cỡ cảnh.")
    else:
        dens = "thua" if "--thua" in sys.argv else "day" if "--day" in sys.argv else "vua"
        p = run(f, dens, p)
        from collections import Counter
        c = Counter(s["k"] for s in p["shots"])
        print(f"Cỡ cảnh: {len(p['shots'])} cảnh — toàn {c['toan']} · trung {c['trung']} · cận {c['can']}")
    pj.write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
