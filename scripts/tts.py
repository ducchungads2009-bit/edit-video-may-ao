"""GIỌNG ĐỌC AI TIẾNG VIỆT — chạy offline trên máy (sherpa-onnx + giọng Piper tiếng Việt).
Lần đầu tự tải: thư viện sherpa-onnx 1.13 (bản 2.x thiếu bộ phát âm cho giọng Piper) vào _cache/tts-lib,
và mô hình giọng (~65MB) vào models/tts/. Sau đó không cần mạng.

  python scripts/tts.py "<folder>" "Nội dung cần đọc" [--giong nu1|nu2|vn:<tên>] [--toc-do 1.0]
  -> in đường dẫn file wav trong dự án (assets/giong-doc/...) và độ dài
  python scripts/tts.py ds    -> danh sách giọng

GIỌNG VieNeu (`--giong vn:Hải Đăng`, `vn:Trúc Ly`… — cách LumReels đọc lời): 25 giọng Bắc / Trung / Nam, tự nhiên hơn Piper, vẫn
chạy trên máy (onnxruntime). Lần đầu tự cài thư viện (~250MB) vào _cache/vieneu-lib và tải mô hình (~600MB) từ huggingface.co —
mạng chặn thì tự quay về giọng nu1 và báo.
"""
import hashlib
import json
import os
import shutil
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


VN_LIB = ROOT / "_cache" / "vieneu-lib"
VN_VOICES = {  # tên: mô tả (VieNeu-TTS, Apache-2.0)
    "Hải Đăng": "Nam · Bắc · tự nhiên (mặc định)", "Trúc Ly": "Nữ · Bắc · tự nhiên", "Ngọc Huyền": "Nữ · Bắc · tự nhiên",
    "Đoan Trang": "Nữ · Bắc · tự nhiên", "Mai Anh": "Nữ · Bắc · tin tức", "Thiện Minh": "Nam · Bắc · kể chuyện",
    "Quốc Tuấn": "Nam · Bắc · tự nhiên", "Xuân Vĩnh": "Nam · Bắc · tự nhiên", "Minh Đức": "Nam · Bắc · tin tức",
    "Thanh Bình": "Nam · Bắc · kể chuyện", "Ngọc Linh": "Nữ · Bắc · kể chuyện", "Quỳnh Anh": "Nữ · Bắc · đọc truyện",
    "Quang Sơn": "Nam · Trung · tự nhiên", "Ngọc Trân": "Nữ · Trung · tự nhiên",
    "Thùy Dung": "Nữ · Nam · tin tức", "Thục Đoan": "Nữ · Nam · kể chuyện", "Mỹ Duyên": "Nữ · Nam · đọc truyện",
    "Kim Thanh": "Nữ · Nam · đọc truyện", "Minh Triết": "Nam · Nam · tin tức", "Thái Sơn": "Nam · Nam · kể chuyện",
    "Đức Trí": "Nam · Nam · đọc truyện", "Adam": "Nam · Nam · tự nhiên",
}
VN_WORKER = r'''
import sys, json
a = json.loads(sys.argv[1])
from vieneu import Vieneu
tts = Vieneu()
err = None
for _ in range(3):  # VieNeu thỉnh thoảng lỗi, thử lại
    try:
        tts.save(tts.infer(a["text"], voice=a["voice"] or None), a["out"]); err = None; break
    except Exception as e:
        err = str(e)
if err:
    raise SystemExit(err)
'''


def ensure_vieneu():
    if (VN_LIB / "vieneu").is_dir():
        return
    print("Cài giọng đọc VieNeu (lần đầu, ~1–2 phút)...", flush=True)
    VN_LIB.mkdir(parents=True, exist_ok=True)
    pip = [sys.executable, "-m", "pip", "install", "-q", "--target", str(VN_LIB)]
    r = subprocess.run(pip + ["--no-deps", "vieneu", "sea-g2p"], capture_output=True, text=True)
    if not r.returncode:  # bỏ gradio / librosa (giao diện web, không cần để đọc)
        r = subprocess.run(pip + ["onnxruntime", "numpy", "soundfile", "soxr", "kaldi-native-fbank", "tokenizers", "huggingface_hub", "PyYAML"],
                           capture_output=True, text=True)
    if r.returncode:
        shutil.rmtree(VN_LIB, ignore_errors=True)
        raise RuntimeError("Không cài được VieNeu: " + (r.stderr or "")[-400:])


def say_vieneu(folder: Path, text: str, name: str, speed: float) -> dict:
    name = name.strip() or "Hải Đăng"
    out_dir = folder / "assets" / "giong-doc"
    out_dir.mkdir(parents=True, exist_ok=True)
    h = hashlib.md5(f"vn|{name}|{speed}|{text}".encode()).hexdigest()[:8]
    out = out_dir / f"giong-ai_{h}.wav"
    if not out.exists():
        ensure_vieneu()
        raw = out_dir / f"_vn_{h}.wav"
        env = {**os.environ, "PYTHONPATH": str(VN_LIB)}
        r = subprocess.run([sys.executable, "-c", VN_WORKER, json.dumps({"text": text, "voice": name, "out": str(raw)}, ensure_ascii=False)],
                           capture_output=True, text=True, env=env, encoding="utf-8", errors="replace", timeout=1800)
        if r.returncode or not raw.exists():
            raise RuntimeError("Lỗi giọng VieNeu: " + (r.stderr or "")[-400:])
        af = ["-af", f"atempo={max(0.5, min(2.0, float(speed))):.4f}"] if abs(float(speed) - 1) > 1e-3 else []
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), *af, "-ar", "48000", "-ac", "1", str(out)], check=True)
        raw.unlink(missing_ok=True)
    import wave
    with wave.open(str(out)) as w:
        dur = w.getnframes() / w.getframerate()
    return {"path": out.relative_to(folder).as_posix(), "dur": round(dur, 2), "voice": f"vn:{name}"}


def say(folder: Path, text: str, voice: str = "nu1", speed: float = 1.0, mode: str = None) -> dict:
    if voice.startswith("vn:") or voice == "vn" or voice in VN_VOICES:
        name = voice[3:] if voice.startswith("vn:") else ("" if voice == "vn" else voice)
        try:
            return say_vieneu(folder, " ".join(text.split()), name, speed)
        except Exception as e:  # noqa
            print(f"[!] Không dùng được giọng VieNeu ({str(e)[:200]}) — đọc bằng giọng nu1", flush=True)
            voice = "nu1"
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
    if len(sys.argv) > 1 and sys.argv[1] == "ds":
        for k, (_, m) in VOICES.items():
            print(f"{k:12} {m} (Piper, có sẵn)")
        for k, m in VN_VOICES.items():
            print(f"vn:{k:10} {m} (VieNeu)")
        sys.exit(0)
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    v = sys.argv[sys.argv.index("--giong") + 1] if "--giong" in sys.argv else "nu1"
    sp = float(sys.argv[sys.argv.index("--toc-do") + 1]) if "--toc-do" in sys.argv else 1.0
    print(json.dumps(say(Path(sys.argv[1]).resolve(), sys.argv[2], v, sp), ensure_ascii=False))
