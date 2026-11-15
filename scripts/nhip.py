"""Dò NHỊP (beat) của nhạc nền — chỉ cần numpy + ffmpeg.
Onset (độ "giật" của tiếng) theo phổ -> tìm tempo bằng tự tương quan -> bắt nhịp bằng quy hoạch động (kiểu Ellis).

  python scripts/nhip.py "<file nhạc>"            # in danh sách giây có nhịp
  beats(path) -> (tempo_bpm, [giây, ...])         # dùng trong gui.py
"""
import json
import subprocess
import sys

SR, HOP, N = 22050, 512, 1024


def _audio(path: str, maxsec: float = 600):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-t", str(maxsec), "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def onset_env(y):
    import numpy as np
    if len(y) < N * 4:
        return np.zeros(1)
    win = np.hanning(N).astype(np.float32)
    nf = 1 + (len(y) - N) // HOP
    idx = np.arange(N)[None, :] + HOP * np.arange(nf)[:, None]
    spec = np.abs(np.fft.rfft(y[idx] * win, axis=1))
    logs = np.log1p(spec * 10)
    flux = np.maximum(0, np.diff(logs, axis=0)).sum(axis=1)
    flux = np.concatenate([[0], flux])
    flux -= np.convolve(flux, np.ones(16) / 16, mode="same")  # bỏ nền chậm
    flux = np.maximum(flux, 0)
    return flux / (flux.max() + 1e-9)


def beats(path: str):
    import numpy as np
    y = _audio(path)
    env = onset_env(y)
    if len(env) < 50:
        return 0.0, []
    fps = SR / HOP
    # tempo: tự tương quan trong khoảng 70–180 BPM, ưu tiên quanh 120
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 70)
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    lags = np.arange(lo, hi + 1)
    w = np.exp(-0.5 * (np.log2(60 * fps / lags / 120) / 1.0) ** 2)
    lag = int(lags[np.argmax(ac[lo:hi + 1] * w)])
    tempo = 60 * fps / lag
    # quy hoạch động: điểm = onset + điểm nhịp trước (phạt lệch khỏi chu kỳ)
    n = len(env)
    score = env.copy()
    back = np.full(n, -1)
    for i in range(n):
        a, b = max(0, i - 2 * lag), i - lag // 2
        if b <= a:
            continue
        prev = np.arange(a, b)
        pen = -100 * (np.log((i - prev) / lag)) ** 2
        cand = score[prev] + pen
        j = int(np.argmax(cand))
        score[i] = env[i] + cand[j]
        back[i] = prev[j]
    # lần ngược từ điểm cao nhất ở cuối
    i = int(np.argmax(score[-lag:])) + n - lag
    out = []
    while i >= 0:
        out.append(i)
        i = back[i]
    out = sorted(out)
    return round(float(tempo), 1), [round(i / fps, 3) for i in out]


def beats_on_video(path: str, start_from: float, total: float):
    """nhịp tính theo giây của video xuất (nhạc bắt đầu ở 0, từ giây start_from của file, tự lặp)"""
    tempo, bs = beats(path)
    if not bs:
        return tempo, []
    import numpy as np
    y_len = len(_audio(path)) / SR
    out, base = [], -start_from
    while base < total and y_len > 1:
        out += [round(b + base, 2) for b in bs if 0 <= b + base < total]
        base += y_len
    return tempo, sorted(set(out))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    t, b = beats(sys.argv[1])
    print(json.dumps({"tempo": t, "beats": b[:400]}))
