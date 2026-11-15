"""GIỌNG ĐỌC AI TIẾNG VIỆT — chạy offline trên máy (sherpa-onnx + giọng Piper tiếng Việt).
Lần đầu tự tải: thư viện sherpa-onnx 1.13 (bản 2.x thiếu bộ phát âm cho giọng Piper) vào _cache/tts-lib,
và mô hình giọng (~65MB) vào models/tts/. Sau đó không cần mạng.

  python scripts/tts.py "<folder>" "Nội dung cần đọc" [--giong nu1|nu2] [--toc-do 1.0]
  -> in đường dẫn file wav trong dự án (assets/giong-doc/...) và độ dài
"""
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "_cache" / "tts-lib"
MODELS = ROOT / "models" / "tts"
BASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/"
VOICES = {  # tên: (thư mục mô hình, mô tả)
    "nu1": ("vits-piper-vi_VN-vais1000-medium", "Giọng nữ rõ (chất lượng cao)"),
    "nu2": ("vits-piper-vi_VN-25hours_single-low", "Giọng nữ nhẹ"),
}


def ensure_lib():
    if (LIB / "sherpa_onnx").is_dir():
        return
    print("Cài thư viện giọng đọc (lần đầu)...", flush=True)
    LIB.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--target", str(LIB), "sherpa-onnx>=1.12,<2"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("Không cài được sherpa-onnx: " + r.stderr[-400:])


def ensure_voice(v: str) -> Path:
    name = VOICES.get(v, VOICES["nu1"])[0]
    d = MODELS / name
    if any(d.glob("*.onnx")):
        return d
    MODELS.mkdir(parents=True, exist_ok=True)
    tmp = MODELS / (name + ".tar.bz2")
    print(f"Tải giọng đọc {v} (lần đầu, ~65MB)...", flush=True)
    urllib.request.urlretrieve(BASE + name + ".tar.bz2", tmp)
    with tarfile.open(tmp) as t:
        t.extractall(MODELS)
    tmp.unlink(missing_ok=True)
    return d


WORKER = r'''
import sys, json, wave, numpy as np, sherpa_onnx
a = json.loads(sys.argv[1])
d = a["dir"]
onnx = [f for f in __import__("os").listdir(d) if f.endswith(".onnx")][0]
cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
    vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=f"{d}/{onnx}", tokens=f"{d}/tokens.txt", data_dir=f"{d}/espeak-ng-data"),
    num_threads=a["threads"]), max_num_sentences=2)
tts = sherpa_onnx.OfflineTts(cfg)
g = tts.generate(a["text"], sid=0, speed=a["speed"])
x = np.clip(np.asarray(g.samples, dtype=np.float32), -1, 1)
with wave.open(a["out"], "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(g.sample_rate)
    w.writeframes((x * 32767).astype(np.int16).tobytes())
print(json.dumps({"dur": len(x) / g.sample_rate}))
'''


def say(folder: Path, text: str, voice: str = "nu1", speed: float = 1.0, mode: str = None) -> dict:
    if voice.startswith("api:"):  # giọng clone qua API (scripts/tts_api.py)
        import tts_api
        return tts_api.say(folder, text, voice[4:] or None, speed, mode)
    text = " ".join(text.split())
    if not text:
        raise ValueError("Chưa có nội dung để đọc")
    ensure_lib()
    d = ensure_voice(voice)
    out_dir = folder / "assets" / "giong-doc"
    out_dir.mkdir(parents=True, exist_ok=True)
    h = hashlib.md5(f"{voice}|{speed}|{text}".encode()).hexdigest()[:8]
    out = out_dir / f"giong-ai_{h}.wav"
    if not out.exists():
        env = {**os.environ, "PYTHONPATH": str(LIB)}
        arg = json.dumps({"dir": str(d), "text": text, "speed": float(speed), "out": str(out), "threads": max(1, (os.cpu_count() or 2) - 1)}, ensure_ascii=False)
        r = subprocess.run([sys.executable, "-c", WORKER, arg], capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
        if r.returncode or not out.exists():
            raise RuntimeError("Lỗi tạo giọng đọc: " + (r.stderr or "")[-500:])
    import wave
    with wave.open(str(out)) as w:
        dur = w.getnframes() / w.getframerate()
    return {"path": out.relative_to(folder).as_posix(), "dur": round(dur, 2)}


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    v = sys.argv[sys.argv.index("--giong") + 1] if "--giong" in sys.argv else "nu1"
    sp = float(sys.argv[sys.argv.index("--toc-do") + 1]) if "--toc-do" in sys.argv else 1.0
    print(json.dumps(say(Path(sys.argv[1]).resolve(), sys.argv[2], v, sp), ensure_ascii=False))
