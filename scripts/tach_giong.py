"""TÁCH GIỌNG NÓI khỏi nhạc nền / tiếng ồn (mô hình UVR MDX-Net Voc_FT, ONNX, chạy offline).
Lần đầu tự tải mô hình (~65MB) vào models/. Kết quả: file chỉ còn giọng (và tuỳ chọn file chỉ còn nhạc).

  python scripts/tach_giong.py "<file vào>" "<file giọng.wav>" [--nhac "<file nhạc.wav>"]
"""
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "models" / "UVR-MDX-NET-Voc_FT.onnx"
URL = "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/UVR-MDX-NET-Voc_FT.onnx"
SR, NFFT, HOP, DIMF, DIMT, COMP = 44100, 7680, 1024, 3072, 256, 1.021


def ensure():
    if not MODEL.exists():
        print("Tải mô hình tách giọng (lần đầu, ~65MB)...", flush=True)
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        tmp = MODEL.with_suffix(".tmp")
        urllib.request.urlretrieve(URL, tmp)
        tmp.replace(MODEL)
    try:
        import onnxruntime  # noqa
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "onnxruntime"], check=False)


def _read(path):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).T.copy()


def _write(path, x):
    import numpy as np
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", str(path)], stdin=subprocess.PIPE)
    p.communicate(np.ascontiguousarray(x.T.astype(np.float32)).tobytes())


def _stft(x, win):
    import numpy as np
    pad = NFFT // 2
    x = np.pad(x, ((0, 0), (pad, pad)), mode="reflect")
    nf = 1 + (x.shape[1] - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(nf)[:, None]
    return np.fft.rfft(x[:, idx] * win, axis=2).transpose(0, 2, 1)  # [2, F, T]


def _istft(S, win, length):
    import numpy as np
    fr = np.fft.irfft(S.transpose(0, 2, 1), n=NFFT, axis=2) * win  # [2, T, N]
    T = fr.shape[1]
    out = np.zeros((2, NFFT + HOP * (T - 1)), np.float32)
    wsum = np.zeros(NFFT + HOP * (T - 1), np.float32)
    for t in range(T):
        out[:, t * HOP:t * HOP + NFFT] += fr[:, t]
        wsum[t * HOP:t * HOP + NFFT] += win ** 2
    out /= np.maximum(wsum, 1e-8)
    pad = NFFT // 2
    return out[:, pad:pad + length]


def separate(src, voc_out, music_out=None, tick=None):
    import numpy as np
    import onnxruntime as ort
    ensure()
    so = ort.SessionOptions()
    so.intra_op_num_threads = max(1, (os.cpu_count() or 2) - 1)
    prov = [p for p in ("CoreMLExecutionProvider", "DmlExecutionProvider") if p in ort.get_available_providers()] + ["CPUExecutionProvider"]
    try:
        sess = ort.InferenceSession(str(MODEL), so, providers=prov)
    except Exception:
        sess = ort.InferenceSession(str(MODEL), so, providers=["CPUExecutionProvider"])
    mix = _read(src)
    n = mix.shape[1]
    win = np.hanning(NFFT + 1)[:-1].astype(np.float32)
    trim = NFFT // 2
    chunk = HOP * (DIMT - 1)
    gen = chunk - 2 * trim
    pad = gen - n % gen
    mp = np.concatenate([np.zeros((2, trim), np.float32), mix, np.zeros((2, pad + trim), np.float32)], axis=1)
    outs = []
    steps = list(range(0, n + pad, gen))
    for k, i in enumerate(steps):
        w = mp[:, i:i + chunk]
        S = _stft(w, win)[:, :, :DIMT]  # [2, F, T]
        if S.shape[2] < DIMT:
            S = np.pad(S, ((0, 0), (0, 0), (0, DIMT - S.shape[2])))
        x = np.concatenate([S.real, S.imag], axis=0)[None, :, :DIMF, :].astype(np.float32)  # [1, 4, DIMF, T]
        y = sess.run(None, {"input": x})[0][0]
        Y = np.zeros((2, NFFT // 2 + 1, DIMT), np.complex64)
        Y[:, :DIMF] = y[:2] + 1j * y[2:]
        outs.append(_istft(Y, win, chunk)[:, trim:trim + gen])
        if tick:
            tick((k + 1) / len(steps))
    voc = np.concatenate(outs, axis=1)[:, :n] * COMP
    _write(voc_out, voc)
    if music_out:
        _write(music_out, mix - voc)
    return voc_out


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    mus = sys.argv[sys.argv.index("--nhac") + 1] if "--nhac" in sys.argv else None
    separate(sys.argv[1], sys.argv[2], mus, lambda f: print(f"Tách giọng {int(f * 100)}%", flush=True))
    print("Xong:", sys.argv[2])
