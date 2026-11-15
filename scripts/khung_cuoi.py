"""Khung cuối dùng để ĐỨNG HÌNH khi video xuất dài hơn video chính (voice / khối kéo quá cuối).
Nhiều video quay điện thoại có vài khung ĐEN ở cuối -> tìm mốc bắt đầu đoạn đen cuối để đứng hình ở khung còn sáng.
Kết quả lưu _work/den-cuoi.json {"key": "...", "from": giây | null}."""
import json
import subprocess
from pathlib import Path


def black_tail(folder: Path, video_rel: str, dur: float):
    """giây bắt đầu đoạn đen ở cuối video (None nếu cuối video không đen)"""
    folder = Path(folder)
    src = folder / video_rel
    if not src.exists():
        return None
    st = src.stat()
    key = f"{video_rel}|{st.st_size}|{int(st.st_mtime)}"
    cf = folder / "_work" / "den-cuoi.json"
    try:
        c = json.loads(cf.read_text(encoding="utf-8"))
        if c.get("key") == key:
            return c.get("from")
    except Exception:
        pass
    win = min(4.0, dur)
    t0 = max(0.0, dur - win)
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t0:.3f}", "-i", str(src), "-t", f"{win:.3f}",
                        "-vf", "scale=48:48,format=gray", "-f", "rawvideo", "-"], capture_output=True)
    data = r.stdout
    out = None
    if data:
        fs = 48 * 48
        frames = [data[i:i + fs] for i in range(0, len(data) - fs + 1, fs)]
        n = len(frames)
        k = n
        while k > 0 and sum(frames[k - 1]) / fs < 14:  # gần như đen
            k -= 1
        if k < n and k > 0:
            out = round(t0 + win * k / n, 3)
    try:
        cf.parent.mkdir(exist_ok=True)
        cf.write_text(json.dumps({"key": key, "from": out}), encoding="utf-8")
    except Exception:
        pass
    return out


def safe_src(folder: Path, video_rel: str, dur: float, t: float) -> float:
    """giây của video gốc để đứng hình thay cho t (lùi khỏi đoạn đen cuối nếu có)"""
    b = black_tail(folder, video_rel, dur)
    if b is not None and t > b - 0.05:
        return max(0.0, b - 0.1)
    return t


if __name__ == "__main__":
    import sys
    f = Path(sys.argv[1]).resolve()
    info = json.loads((f / "_work" / "info.json").read_text(encoding="utf-8"))
    print(black_tail(f, info["video"], info["durationSec"]))
