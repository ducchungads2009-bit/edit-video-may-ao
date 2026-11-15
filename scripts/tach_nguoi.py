"""TÁCH NGƯỜI khỏi nền để đặt ảnh/video minh họa (hoặc chữ) RA SAU người.

Element nào trong plan.json có "behind": true sẽ nằm sau người. Script này tách người (mô hình Robust Video Matting,
chạy offline bằng onnxruntime) đúng những đoạn cần, lưu _work/nguoi/nguoi_<khung đầu>_<khung cuối>.webm (video nền
trong suốt). render.py tự gọi script này trước khi xuất; trình chỉnh sửa có nút "Tách người".

Dùng:  python scripts/tach_nguoi.py "<folder>"          tách các đoạn còn thiếu theo plan.json hiện tại
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "models" / "rvm_mobilenetv3_fp32.onnx"
MODEL_URL = "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx"
FPS = 30
EXT = 6  # = TR trong EditPlan.tsx (số khung mờ chồng ở điểm nối)
W, H = 1080, 1920
MW, MH = 540, 960  # cỡ đưa vào mô hình (nhanh); mặt nạ phóng lại 1080x1920


def _suffix(plan: dict) -> str:
    try:
        from beauty import suffix
        return suffix(plan.get("beauty") or {})
    except Exception:
        return ""


CH = 150  # khúc 5 giây (khung video gốc): lớp người tách theo khúc cố định -> dời khối không phải tách lại


def behind_of(e) -> bool:
    """khối nằm sau người: lớp z < 0 (hoặc "behind": true khi chưa có z) — giống isBehind() trong EditPlan.tsx"""
    z = e.get("z")
    if e.get("type") == "orbit":  # vòng quay quanh người: nửa sau nằm sau người (trừ khi "behind": false)
        return e.get("behind") is not False
    return z < 0 if isinstance(z, (int, float)) else bool(e.get("behind"))


def pieces(plan: dict, dur0: float) -> list:
    """các mẩu lớp người cần dùng: [{i: đoạn số, from: khung xuất, len, ext, off: khung bắt đầu trong file, A, B: khung gốc
    của cả khúc, file}] — PHẢI giống hệt personPieces() trong editor/logic.ts."""
    segs = [s for s in (plan.get("segments") or []) if s[1] - s[0] > 0.05] or [[0, dur0]]
    want = sorted((round(e["start"] * FPS), round(e["end"] * FPS)) for e in plan.get("elements", [])
                  if e and behind_of(e) and e.get("end", 0) > e.get("start", 0) and e.get("type") not in ("audio", "zoom", "sfx"))
    merged = []
    for a, b in want:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out, acc = [], 0.0
    sfx = _suffix(plan)  # đã làm đẹp -> tách từ video đã làm đẹp, tên file khác
    last = round(dur0 * FPS)
    for i, (a, b) in enumerate(segs):
        f0 = round(acc * FPS)
        acc += b - a
        f1 = round(acc * FPS)
        A0 = round(a * FPS)
        for x0, x1 in merged:
            s, e = max(x0, f0), min(x1, f1)
            if e - s < 1:
                continue
            S, E = A0 + (s - f0), A0 + (e - f0)
            # chạm cuối đoạn (không phải đoạn cuối): dùng dư EXT khung cho kiểu chuyển mờ chồng (đoạn trước chạy dài thêm)
            ext_all = EXT if (e == f1 and i < len(segs) - 1) else 0
            while S < E:
                c = S // CH
                cs, ce = c * CH, (c + 1) * CH
                pe = min(E, ce)
                ext = ext_all if pe == E else 0
                out.append({"i": i, "from": f0 + (S - A0), "len": pe - S, "ext": ext, "off": S - cs, "A": cs, "B": min(last, ce + EXT),
                            "file": f"nguoi_k{c}{sfx}.webm"})
                S = pe
    return out


def ensure_model():
    if MODEL.exists():
        return
    import urllib.request
    print("Tải mô hình tách người (lần đầu, ~15MB)...")
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    tmp = MODEL.with_suffix(".tmp")
    urllib.request.urlretrieve(MODEL_URL, tmp)
    tmp.replace(MODEL)


def ensure_ort():
    try:
        import onnxruntime  # noqa
    except ImportError:
        print("Cài onnxruntime (lần đầu)...")
        subprocess.run([sys.executable, "-m", "pip", "install", "onnxruntime"], check=False)


def cutout(video: Path, A: int, B: int, out: Path, sess, tick=None):
    """khung A..B (30fps) của video -> webm VP9 có kênh trong suốt (người giữ lại, nền trong suốt)."""
    import numpy as np
    n = B - A
    vf = f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},format=rgb24"
    dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{A / FPS:.4f}", "-i", str(video), "-frames:v", str(n),
                            "-vf", vf, "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    tmp = out.with_suffix(".tmp.webm")
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libvpx-vp9", "-threads", str(os.cpu_count() or 4), "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "30",
                            "-deadline", "realtime", "-cpu-used", "8", "-row-mt", "1", "-auto-alt-ref", "0", str(tmp)],
                           stdin=subprocess.PIPE)
    rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4
    dr = np.array([0.4], np.float32)
    # chạy mồi vài khung đầu để mô hình "làm quen" (trạng thái hồi quy), tránh viền nhấp nháy ở khung đầu
    first = None
    k = 0
    fsz = W * H * 3
    while k < n:
        buf = dec.stdout.read(fsz)
        if len(buf) < fsz:
            break
        img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        small = img[::2, ::2] if (MW, MH) == (W // 2, H // 2) else img
        x = (small.astype(np.float32) / 255.0).transpose(2, 0, 1)[None]
        if first is None:
            first = x
            for _ in range(3):
                o = sess.run(None, {"src": x, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3], "downsample_ratio": dr})
                rec = o[2:]
        o = sess.run(None, {"src": x, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3], "downsample_ratio": dr})
        rec = o[2:]
        pha = o[1][0, 0]
        a = np.clip(pha * 255.0, 0, 255).astype(np.uint8)
        a = np.repeat(np.repeat(a, 2, 0), 2, 1)[:H, :W] if a.shape != (H, W) else a
        rgba = np.dstack([img, a])
        enc.stdin.write(rgba.tobytes())
        k += 1
        if tick:
            tick(k / max(1, n))
    dec.stdout.close()
    dec.wait()
    enc.stdin.close()
    enc.wait()
    if enc.returncode or not tmp.exists():
        raise RuntimeError("Không ghi được video tách người")
    tmp.replace(out)


def run(folder: Path, plan: dict = None, video_rel: str = None) -> list:
    """tách các đoạn còn thiếu; trả danh sách đoạn (kèm file)."""
    folder = Path(folder)
    info = json.loads((folder / "_work" / "info.json").read_text(encoding="utf-8"))
    plan = plan or json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    ps = pieces(plan, info["durationSec"])
    d = folder / "_work" / "nguoi"
    seen, todo = set(), []
    for p in ps:  # mỗi khúc tách 1 lần
        if p["file"] not in seen and not (d / p["file"]).exists():
            seen.add(p["file"])
            todo.append(p)
    if not todo:
        return ps
    ensure_ort()
    ensure_model()
    import onnxruntime as ort
    d.mkdir(parents=True, exist_ok=True)
    so = ort.SessionOptions()
    so.intra_op_num_threads = max(1, (os.cpu_count() or 2) - 1)  # dùng hết nhân CPU
    avail = ort.get_available_providers()
    # Mac chip Apple: CoreML (GPU/Neural Engine); Windows có onnxruntime-directml: DirectML (GPU)
    prov = [p for p in ("CoreMLExecutionProvider", "DmlExecutionProvider") if p in avail] + ["CPUExecutionProvider"]
    try:
        sess = ort.InferenceSession(str(MODEL), sess_options=so, providers=prov)
        import numpy as np  # chạy thử 2 lượt (trạng thái đổi cỡ) — lỗi thì quay về CPU
        z = [np.zeros([1, 1, 1, 1], np.float32)] * 4
        o = sess.run(None, {"src": np.zeros([1, 3, MH, MW], np.float32), "r1i": z[0], "r2i": z[1], "r3i": z[2], "r4i": z[3],
                            "downsample_ratio": np.array([0.4], np.float32)})
        sess.run(None, {"src": np.zeros([1, 3, MH, MW], np.float32), "r1i": o[2], "r2i": o[3], "r3i": o[4], "r4i": o[5],
                        "downsample_ratio": np.array([0.4], np.float32)})
    except Exception:
        sess = ort.InferenceSession(str(MODEL), sess_options=so, providers=["CPUExecutionProvider"])
    video = folder / (video_rel or info["video"])
    if video_rel is None and _suffix(plan):  # chạy riêng (nút "Tách người") khi có làm đẹp -> làm đẹp trước
        from beauty import process as beautify
        video = folder / beautify(folder, info["video"], plan.get("beauty") or {}, plan.get("segments"))
    tien = None
    try:
        from tiendo import Tien
        tien = Tien(folder, "tachnguoi", sum(p["B"] - p["A"] for p in todo) / FPS)
    except Exception:  # noqa
        pass
    total = sum(p["B"] - p["A"] for p in todo)
    done = 0
    t0 = time.time()
    for p in todo:
        ln = p["B"] - p["A"]
        print(f"Tách người: khung {p['A']}–{p['B']} ({ln / FPS:.1f}s)...", flush=True)
        base = done
        cutout(video, p["A"], p["B"], d / p["file"], sess,
               (lambda f, base=base, ln=ln: tien and tien.update((base + f * ln) / total, f"Tách người {int((base + f * ln) / total * 100)}%")))
        done += ln
    if tien:
        tien.done(True)
    print(f"Xong tách người: {len(todo)} đoạn, {total / FPS:.1f}s video, mất {time.time() - t0:.0f}s")
    return ps


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    pl = None
    if "--plan" in sys.argv:  # trình chỉnh sửa gửi plan chưa lưu (tự tách phần mới khi dời khối)
        pl = json.loads(Path(sys.argv[sys.argv.index("--plan") + 1]).read_text(encoding="utf-8"))
    r = run(Path(sys.argv[1]).resolve(), pl)
    print(f"{len(r)} đoạn có lớp người." if r else "Không có element nào đặt sau người (\"behind\": true).")
