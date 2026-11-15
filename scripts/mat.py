"""Dò vùng MẶT người trong video chính (để xếp chữ tránh mặt).
Lấy 2 khung/giây (ảnh nhỏ), dò mặt (OpenCV YuNet — models/face_detection_yunet_2023mar.onnx, nhận cả mặt nghiêng; thiếu thì Haar), làm mượt theo thời gian (±1 giây),
giữ mặt lớn nhất mỗi lúc. Kết quả _work/mat.json:
  {"step": 0.5, "w": 1080, "h": 1920, "faces": [[t, x, y, w, h] | [t], ...], "big": tỉ lệ thời gian mặt to}
  toạ độ theo khung 1080x1920 của video chính (giây trong video chính, TRƯỚC khi cắt đoạn).
"Vùng tránh" của chữ = hộp mặt nới rộng (xem zone()): trán, cằm, cổ.

  python scripts/mat.py "<folder>"
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
STEP = 0.5
SW, SH = 270, 480  # khung nhỏ để dò (1/4)


def zone(f):
    """hộp mặt -> vùng chữ cần tránh (nới: trên 25% (tóc), dưới 30% (cằm, cổ), ngang 20%) — giống faceZone() trong editor"""
    _, x, y, w, h = f
    return [max(0, x - w * 0.2), max(0, y - h * 0.25), min(1080, x + w * 1.2), min(1920, y + h * 1.3)]


YUNET = ROOT / "models" / "face_detection_yunet_2023mar.onnx"


def detect(video: Path, dur: float):
    from beauty import ensure_cv2, CASCADE
    ensure_cv2()
    import cv2
    import numpy as np
    yn = None
    if YUNET.exists() and hasattr(cv2, "FaceDetectorYN"):  # bộ dò mạng nơ-ron nhỏ: nhận cả mặt nghiêng
        try:
            yn = cv2.FaceDetectorYN.create(str(YUNET), "", (SW, SH), 0.6, 0.3, 20)
        except Exception:
            yn = None
    front = None
    if yn is None:
        if not hasattr(cv2, "CascadeClassifier"):
            raise RuntimeError("OpenCV này không có YuNet lẫn Haar (CascadeClassifier) — cài: pip install \"opencv-python-headless<5\"")
        base = Path(cv2.data.haarcascades) if hasattr(cv2, "data") else Path(".")
        front = cv2.CascadeClassifier(str(CASCADE if CASCADE.exists() else base / "haarcascade_frontalface_default.xml"))
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", str(video), "-vf", f"fps={1 / STEP},scale={SW}:{SH}",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    raw, k = [], 0
    n = SW * SH * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        img = np.frombuffer(buf, np.uint8).reshape(SH, SW, 3)
        found = []
        if yn is not None:
            r = yn.detect(img)[1]
            if r is not None:
                found = [tuple(float(v) for v in x[:4]) for x in r]
        else:
            g = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
            found = [tuple(map(float, x)) for x in front.detectMultiScale(g, 1.1, 5, minSize=(22, 22))]
        best = max(found, key=lambda r: r[2] * r[3]) if found else None
        if best is not None:
            x, y, w, h = best
            x, y = max(0.0, x), max(0.0, y)
            raw.append([round(k * STEP, 2), int(x * 4), int(y * 4), int(min(SW - x, w) * 4), int(min(SH - y, h) * 4)])
        else:
            raw.append([round(k * STEP, 2)])
        k += 1
    p.wait()
    return raw


def smooth(raw):
    """lấp chỗ dò hụt (≤ 1 giây) và lấy trung vị trong cửa sổ ±1 giây cho hộp đỡ giật"""
    import statistics as st
    out = []
    for i, r in enumerate(raw):
        win = [x for x in raw[max(0, i - 2): i + 3] if len(x) == 5]
        if len(r) == 5 or len(win) >= 2:
            src = win if win else [r]
            out.append([r[0], *(int(st.median(x[j] for x in src)) for j in range(1, 5))])
        else:
            out.append([r[0]])
    return out


def run(folder: Path):
    work = folder / "_work"
    info = json.loads((work / "info.json").read_text(encoding="utf-8"))
    video = folder / info["video"]
    faces = smooth(detect(video, float(info["durationSec"])))
    hit = [f for f in faces if len(f) == 5]
    big = sum(1 for f in hit if f[3] * f[4] > 1080 * 1920 * 0.035) / max(1, len(faces))
    (work / "mat.json").write_text(json.dumps({"step": STEP, "w": 1080, "h": 1920, "faces": faces, "big": round(big, 2)}), encoding="utf-8")
    print(f"Dò mặt: thấy mặt ở {len(hit)}/{len(faces)} mốc, mặt to (nhân vật chiếm nhiều khung) {int(big * 100)}% thời lượng")
    return faces


def at(faces, t, step=STEP):
    """hộp mặt ở giây t (video chính) hoặc None"""
    if not faces:
        return None
    i = min(len(faces) - 1, max(0, round(t / step)))
    f = faces[i]
    return f if len(f) == 5 else None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Dùng: python scripts/mat.py "<folder>"')
    run(Path(sys.argv[1]).resolve())
