"""Làm mượt điểm cắt: dời mép mỗi đoạn (segments trong plan.json) tới chỗ LẶNG nhất gần đó (±0,15s),
để không cắt giữa một từ / giữa hơi. Khối đồ hoạ, phụ đề sửa tay, điểm chớp... tự dời theo cho khớp.

Dùng:  python scripts/snap.py "<folder>"            -> sửa plan.json (giữ bản cũ ở _work/plan_truoc_snap.json)
       python scripts/snap.py "<folder>" --xem      -> chỉ in ra sẽ dời bao nhiêu, không sửa
"""
import json
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WIN = 0.15   # tìm trong khoảng ± giây quanh mép đoạn
STEP = 0.01  # đo âm lượng mỗi 10ms


def energy(folder: Path, video_rel: str):
    """Âm lượng (RMS) mỗi 10ms của video chính — lưu tạm _work/_snap.npy theo kích thước/ngày sửa file."""
    import numpy as np
    src = folder / video_rel
    st = src.stat()
    cache = folder / "_work" / "_snap.npy"
    meta = folder / "_work" / "_snap.json"
    key = f"{video_rel}|{st.st_size}|{int(st.st_mtime)}"
    if cache.exists() and meta.exists() and json.loads(meta.read_text(encoding="utf-8")).get("key") == key:
        return np.load(cache)
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-vn", "-af", "aresample=async=1:first_pts=0", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                       capture_output=True)
    a = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    hop = int(16000 * STEP)
    n = len(a) // hop
    rms = np.sqrt((a[: n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-10)
    db = 20 * np.log10(rms)
    np.save(cache, db)
    meta.write_text(json.dumps({"key": key}), encoding="utf-8")
    return db


def quiet_point(db, t: float, lo: float, hi: float, total: float) -> float:
    """giây có âm lượng nhỏ nhất (làm mượt 30ms) trong [t+lo, t+hi]; ngang nhau thì chọn gần t nhất."""
    import numpy as np
    i0 = max(0, int((t + lo) / STEP))
    i1 = min(len(db) - 1, int((t + hi) / STEP))
    if i1 <= i0 + 2:
        return t
    seg = np.convolve(db[i0:i1 + 1], np.ones(3) / 3, mode="same")
    near = np.abs(np.arange(i0, i1 + 1) * STEP - t)
    cur = int(round(t / STEP)) - i0
    if 0 <= cur < len(seg) and seg[cur] - seg.min() < 2.0:  # đã đủ lặng -> giữ nguyên (bấm nhiều lần không trôi)
        return t
    k = int(np.argmin(seg + near * 8))  # ưu tiên nhẹ chỗ gần mép cũ (8 dB / giây)
    return round(min(total, max(0.0, (i0 + k) * STEP)), 2)


def remapper(old, new):
    """hàm đổi mốc trên video xuất: theo đoạn cũ -> theo đoạn mới (cùng nội dung)."""
    st_o, st_n, acc_o, acc_n = [], [], 0.0, 0.0
    for (a, b), (c, d) in zip(old, new):
        st_o.append(acc_o)
        st_n.append(acc_n)
        acc_o += b - a
        acc_n += d - c

    def f(t: float) -> float:
        for i in range(len(old)):
            a, b = old[i]
            if t < st_o[i] + (b - a) - 1e-6 or i == len(old) - 1:
                src = a + max(0.0, t - st_o[i])
                c, d = new[i]
                return round(st_n[i] + min(d - c, max(0.0, src - c)), 2)
        return t
    return f


def snap_plan(plan: dict, folder: Path):
    info = json.loads((folder / "_work" / "info.json").read_text(encoding="utf-8"))
    total = info["durationSec"]
    segs = [[float(a), float(b)] for a, b in plan.get("segments") or []]
    if not segs:
        return plan, []
    db = energy(folder, info["video"])
    new, changes = [], []
    for i, (a, b) in enumerate(segs):
        na = a if i and abs(segs[i - 1][1] - a) < 0.05 else quiet_point(db, a, -WIN, WIN * 0.8, total)
        nb = b if i < len(segs) - 1 and abs(segs[i + 1][0] - b) < 0.05 else quiet_point(db, b, -WIN * 0.8, WIN, total)
        if nb - na < 0.2:
            na, nb = a, b
        new.append([na, nb])
        if abs(na - a) >= 0.01 or abs(nb - b) >= 0.01:
            changes.append({"doan": i + 1, "truoc": [a, b], "sau": [na, nb]})
    if not changes:
        return plan, []
    f = remapper(segs, new)
    p = json.loads(json.dumps(plan))
    p["segments"] = new
    for e in p.get("elements", []):
        s, en = f(e["start"]), f(max(e["start"], e["end"] - 1e-3))
        e["start"], e["end"] = s, round(max(s + 0.2, en), 2)
        for it in e.get("items") or []:
            it["at"] = f(it["at"])
    if isinstance(p.get("captions"), list):
        for pg in p["captions"]:
            for w in pg:
                w["start"], w["end"] = f(w["start"]), max(f(w["start"]) + 0.05, f(w["end"]))
    if isinstance(p.get("cuts"), list):
        p["cuts"] = [f(c) for c in p["cuts"]]
    if isinstance(p.get("joinFx"), dict):  # khoá điểm nối đổi theo mép mới
        old_keys = {f"{round(segs[i][1], 2)}>{round(segs[i + 1][0], 2)}": f"{round(new[i][1], 2)}>{round(new[i + 1][0], 2)}"
                    for i in range(len(segs) - 1)}
        p["joinFx"] = {old_keys.get(k, k): v for k, v in p["joinFx"].items()}
    return p, changes


def main(folder: Path):
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    p, changes = snap_plan(plan, folder)
    if not changes:
        print("Không cần dời: các điểm cắt đã nằm ở chỗ lặng (hoặc chưa có segments).")
        return
    for c in changes:
        da, dbb = c["sau"][0] - c["truoc"][0], c["sau"][1] - c["truoc"][1]
        print(f"Đoạn {c['doan']}: đầu {da * 1000:+.0f}ms, cuối {dbb * 1000:+.0f}ms")
    if "--xem" in sys.argv:
        return
    (folder / "_work" / "plan_truoc_snap.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    (folder / "plan.json").write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Đã làm mượt {len(changes)} đoạn (bản cũ: _work/plan_truoc_snap.json)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Dùng: python scripts/snap.py "<folder>" [--xem]')
    main(Path(sys.argv[1]).resolve())
