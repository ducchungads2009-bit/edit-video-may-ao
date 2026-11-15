"""Kiểm tra TIẾNG–HÌNH có khớp không trong file đã xuất (so với video gốc), từng đoạn.

Dùng:  python scripts/dongbo.py "<folder>" [file.mp4]      (mặc định <folder>/final.mp4)
render.py tự chạy sau mỗi lần xuất. Kết quả: _work/dong-bo.json + in ra màn hình.

Cách làm: với mỗi đoạn giữ lại (segments), so đường bao âm lượng của bản xuất với tiếng gốc (ra độ trễ của tiếng) và so
nhịp chuyển động của hình với hình gốc (ra độ trễ của hình). Lệch tiếng–hình = trễ tiếng − trễ hình.
|lệch| ≤ 45 ms: khớp (mắt không thấy) · 45–90 ms: hơi lệch · > 90 ms: lệch rõ (thấy miệng không khớp tiếng).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SR = 8000      # mẫu/giây khi giải mã tiếng
BIN = 40       # 5 ms / ô đường bao
GW, GH = 72, 128


def _audio(path: Path, t0: float, dur: float) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{max(0, t0):.3f}", "-t", f"{dur:.3f}", "-i", str(path),
                        "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True)
    x = np.abs(np.frombuffer(r.stdout, np.int16).astype(np.float32))
    n = len(x) // BIN
    return x[: n * BIN].reshape(n, BIN).mean(1)


def _motion(path: Path, t0: float, dur: float) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{max(0, t0):.3f}", "-t", f"{dur:.3f}", "-i", str(path),
                        "-an", "-vf", f"fps=30,scale={GW}:{GH},format=gray", "-f", "rawvideo", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8)
    n = len(a) // (GW * GH)
    if n < 3:
        return np.zeros(0)
    f = a[: n * GW * GH].reshape(n, GH, GW).astype(np.int16)
    return np.abs(np.diff(f, axis=0)).mean(axis=(1, 2)).astype(np.float32)


def _lag(ref: np.ndarray, sig: np.ndarray, pad: int, maxlag: int):
    """ref được lấy rộng hơn `pad` ô mỗi bên; tìm độ trễ của sig so với ref. Trả (lag, độ tin cậy 0–1)."""
    if len(sig) < 20 or len(ref) < len(sig):
        return None, 0.0
    s = (sig - sig.mean()) / (sig.std() + 1e-6)
    best, scores = None, []
    for k in range(pad - maxlag, pad + maxlag + 1):
        if k < 0 or k + len(s) > len(ref):
            scores.append(-1)
            continue
        w = ref[k:k + len(s)]
        w = (w - w.mean()) / (w.std() + 1e-6)
        scores.append(float((w * s).mean()))
    scores = np.array(scores)
    i = int(scores.argmax())
    best = pad - (i + pad - maxlag)  # dương = sig trễ hơn ref
    conf = float(scores[i])
    return best, conf


def check(folder: Path, final: Path = None) -> dict:
    folder = Path(folder)
    final = Path(final) if final else folder / "final.mp4"
    info = json.loads((folder / "_work" / "info.json").read_text(encoding="utf-8"))
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8")) if (folder / "plan.json").exists() else {}
    src = folder / info["video"]
    segs = [s for s in (plan.get("segments") or []) if s[1] - s[0] > 0.05] or [[0, info["durationSec"]]]
    # khoảng bị che bởi ảnh trám (hình khác gốc) -> bỏ khi so hình
    cover = [(e["start"], e["end"]) for e in plan.get("elements", []) if e.get("type") == "broll"]
    out, acc = [], 0.0
    for a, b in segs:
        o0, d = acc, b - a
        acc += d
        if d < 2.2:
            continue
        m = 0.4  # bỏ mép đoạn (vuốt tiếng, chuyển cảnh)
        L = min(d - 2 * m, 12.0)
        oc = o0 + m
        pad = 0.5
        # tiếng
        ref = _audio(src, a + m - pad, L + 2 * pad)
        sig = _audio(final, oc, L)
        al, ac = _lag(ref, sig, int(pad * 1000 / 5), 100)
        # hình (bỏ nếu bị ảnh trám che)
        vl, vc = None, 0.0
        if not any(s < oc + L and e > oc for s, e in cover):
            refv = _motion(src, a + m - pad, L + 2 * pad)
            sigv = _motion(final, oc, L)
            vl, vc = _lag(refv, sigv, int(pad * 30), 12)
        item = {"doan": [round(a, 2), round(b, 2)], "giayXuat": round(o0, 2),
                "treTieng_ms": None if al is None else al * 5, "tinCayTieng": round(ac, 2),
                "treHinh_ms": None if vl is None else round(vl * 1000 / 30), "tinCayHinh": round(vc, 2)}
        if al is not None and ac > 0.4:
            vms = item["treHinh_ms"] if (vl is not None and vc > 0.4) else 0
            item["lech_ms"] = item["treTieng_ms"] - vms
        out.append(item)
    vals = [x["lech_ms"] for x in out if "lech_ms" in x]
    med = float(np.median(vals)) if vals else None
    verdict = ("không đủ dữ liệu để đo" if med is None else "khớp" if abs(med) <= 45 else
               "hơi lệch" if abs(med) <= 90 else "LỆCH RÕ")
    res = {"file": final.name, "lech_ms": None if med is None else round(med), "ketLuan": verdict,
           "ghiChu": "lệch > 0: tiếng TRỄ hơn hình; < 0: tiếng SỚM hơn hình", "doan": out}
    (folder / "_work" / "dong-bo.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def report(res: dict) -> str:
    if res["lech_ms"] is None:
        return "Đồng bộ tiếng–hình: không đủ dữ liệu để đo."
    s = f"Đồng bộ tiếng–hình: {res['ketLuan']} (lệch {res['lech_ms']:+d} ms"
    s += ", tiếng trễ hơn hình)" if res["lech_ms"] > 0 else ", tiếng sớm hơn hình)" if res["lech_ms"] < 0 else ")"
    if res["ketLuan"] != "khớp":
        s += "\n[!] Tiếng và hình không khớp — xem _work/dong-bo.json (từng đoạn)."
    return s


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    r = check(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None)
    print(report(r))
    for x in r["doan"]:
        print(f"  đoạn {x['doan']} (giây {x['giayXuat']}): tiếng {x['treTieng_ms']} ms (tin {x['tinCayTieng']}), "
              f"hình {x['treHinh_ms']} ms (tin {x['tinCayHinh']}) -> lệch {x.get('lech_ms', '?')}")
