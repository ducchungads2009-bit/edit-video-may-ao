"""(dành cho người phát triển) Tạo thư viện hiệu ứng âm thanh bằng tổng hợp số -> public/sfx/*.wav + sfx.json.
Không có bản quyền bên thứ ba. Chạy: python scripts/_tao_sfx.py"""
import json
import wave
from pathlib import Path

import numpy as np

SR = 48000
OUT = Path(__file__).resolve().parent.parent / "public" / "sfx"
rng = np.random.default_rng(7)


def t(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.005, r=0.2, shape=3.0):
    """đường bao: lên nhanh (a giây), tắt dần mũ"""
    x = np.arange(n) / SR
    e = np.minimum(1, x / max(a, 1e-4))
    return e * np.exp(-shape * x / max(r, 1e-4))


def lp(x, cut):
    """lọc thông thấp 1 cực (cut: Hz, có thể là mảng theo thời gian)"""
    if np.ndim(cut) == 0:
        from scipy.signal import lfilter
        a = np.exp(-2 * np.pi * cut / SR)
        return lfilter([1 - a], [1, -a], x)
    cut = np.asarray(cut, float)
    a = np.exp(-2 * np.pi * cut / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def hp(x, cut):
    return x - lp(x, cut)


def bp(x, lo, hi):
    return lp(hp(x, lo), hi)


def sweep(f0, f1, d, kind="exp"):
    tt = t(d)
    f = f0 * (f1 / f0) ** (tt / d) if kind == "exp" else f0 + (f1 - f0) * tt / d
    return np.sin(2 * np.pi * np.cumsum(f) / SR), f


def norm(x, peak=0.89):
    m = np.abs(x).max() or 1
    return x / m * peak


def save(name, x):
    x = norm(x)
    fade = min(len(x), int(0.004 * SR))
    x[-fade:] *= np.linspace(1, 0, fade)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def whoosh(d, f0, f1, peak_at=0.6, bright=1.0):
    n = int(SR * d)
    noise = rng.standard_normal(n)
    tt = np.arange(n) / n
    cut = f0 + (f1 - f0) * np.sin(np.pi * np.clip(tt / peak_at * 0.5, 0, 1)) ** 2
    y = lp(hp(noise, 150), cut * bright)
    e = np.sin(np.pi * np.clip(tt, 0, 1)) ** 1.5
    e *= np.where(tt < peak_at, (tt / peak_at) ** 1.2, np.exp(-4 * (tt - peak_at) / (1 - peak_at)))
    return y * e


def tone(f, d, a=0.002, r=0.3, harm=(1, 0.3, 0.1)):
    tt = t(d)
    y = sum(h * np.sin(2 * np.pi * f * (k + 1) * tt) for k, h in enumerate(harm))
    return y * env(len(tt), a, r)


LIB = []


def add(name, cat, desc, use, x):
    save(name, x)
    LIB.append({"name": name, "cat": cat, "desc": desc, "use": use, "dur": round(len(x) / SR, 2)})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # --- chuyển cảnh ---
    add("whoosh", "chuyen-canh", "Vụt gió vừa", "chuyển cảnh, ảnh trám trượt vào, chữ bay vào", whoosh(0.55, 400, 5500))
    add("whoosh-nhe", "chuyen-canh", "Vụt gió nhẹ, mềm", "mờ chồng, chữ hiện mờ→nét, phong cách nhẹ nhàng", whoosh(0.7, 300, 2500) * 0.7)
    add("whoosh-manh", "chuyen-canh", "Vụt gió mạnh, sắc", "lia nhanh (whip), zoom xuyên, chuyển cảnh mạnh", whoosh(0.45, 600, 9000, 0.5, 1.2))
    add("swoosh", "chuyen-canh", "Lướt ngắn", "trượt chữ/nhãn, đẩy cảnh", whoosh(0.28, 900, 7000, 0.45))
    add("swipe", "chuyen-canh", "Quẹt rất ngắn", "đổi chữ nhanh, quẹt màn hình", whoosh(0.16, 1500, 9000, 0.4) * 0.8)
    s, f = sweep(120, 1600, 1.1)
    noise = lp(rng.standard_normal(len(s)), np.linspace(400, 9000, len(s)))
    add("riser", "chuyen-canh", "Dâng lên căng dần (1,1s)", "trước câu chốt / tiết lộ / con số lớn", (0.6 * s + 0.5 * noise) * np.linspace(0, 1, len(s)) ** 2)
    # --- nhấn mạnh ---
    tt = t(0.9)
    boom = np.sin(2 * np.pi * (55 + 90 * np.exp(-tt * 18)) * tt) * env(len(tt), 0.002, 0.35, 2.5)
    add("impact", "nhan-manh", "Đập mạnh, trầm", "zoom giật, chữ to đập vào, con số gây sốc", boom + 0.4 * lp(rng.standard_normal(len(tt)), 900) * env(len(tt), 0.001, 0.08))
    tt = t(1.6)
    add("boom", "nhan-manh", "Bùm trầm vang dài", "mở đầu hook, tiêu đề lớn", np.sin(2 * np.pi * (40 + 60 * np.exp(-tt * 10)) * tt) * env(len(tt), 0.003, 0.9, 2.2)
        + 0.3 * lp(rng.standard_normal(len(tt)), 400) * env(len(tt), 0.002, 0.4))
    tt = t(0.25)
    add("hit", "nhan-manh", "Gõ chắc, ngắn", "từ khóa bật ra, nhấn nhịp", np.sin(2 * np.pi * (180 * np.exp(-tt * 25) + 70) * tt) * env(len(tt), 0.001, 0.07)
        + 0.5 * bp(rng.standard_normal(len(tt)), 800, 5000) * env(len(tt), 0.0005, 0.02))
    # --- hiện chữ / giao diện ---
    tt = t(0.12)
    add("pop", "hien-chu", "Bốp nhẹ", "chữ/nhãn bật ra (mặc định)", np.sin(2 * np.pi * (900 * np.exp(-tt * 45) + 300) * tt) * env(len(tt), 0.001, 0.035))
    tt = t(0.18)
    add("bubble", "hien-chu", "Bong bóng (tròn, vui)", "nhãn dán, emoji, chữ vui", np.sin(2 * np.pi * (400 + 1400 * (tt / 0.18) ** 0.6) * tt) * env(len(tt), 0.002, 0.06))
    tt = t(0.05)
    add("click", "hien-chu", "Click giao diện", "hiện icon, đổi mục, checklist nhỏ", bp(rng.standard_normal(len(tt)), 1500, 8000) * env(len(tt), 0.0003, 0.008) + 0.4 * np.sin(2 * np.pi * 2200 * tt) * env(len(tt), 0.0003, 0.01))
    tt = t(0.06)
    add("tick", "hien-chu", "Tích khẽ", "nhãn icon (chip) hiện ra", np.sin(2 * np.pi * 3200 * tt) * env(len(tt), 0.0003, 0.012))
    keys = np.zeros(int(SR * 1.2))
    pos = 0
    while pos < len(keys) - 4000:
        n = 2500
        k = bp(rng.standard_normal(n), 1200 + rng.random() * 1500, 7000) * env(n, 0.0003, 0.012)
        keys[pos:pos + n] += k * (0.6 + 0.4 * rng.random())
        pos += int(SR * (0.07 + 0.08 * rng.random()))
    add("typing", "hien-chu", "Gõ phím (1,2s)", "chữ gõ từng ký tự", keys)
    # --- vui ---
    tt = t(0.5)
    add("boing", "vui", "Lò xo nảy", "nhãn dán nảy, khoảnh khắc hài", np.sin(2 * np.pi * np.cumsum(220 + 120 * np.sin(2 * np.pi * 14 * tt) * np.exp(-tt * 5)) / SR) * env(len(tt), 0.002, 0.25))
    notes = [523.25, 659.25, 783.99, 1046.5]
    tada = np.zeros(int(SR * 0.9))
    for k, fz in enumerate(notes):
        x = tone(fz, 0.5, 0.003, 0.25, (1, 0.4, 0.15))
        o = int(SR * 0.08 * k)
        tada[o:o + len(x)] += x[: len(tada) - o]
    add("tada", "vui", "Ta-da (hợp âm lên)", "kết quả tốt, hoàn thành, tiết lộ vui", tada)
    # --- thông báo / tiền ---
    add("ding", "thong-bao", "Ding trong", "mỗi dòng checklist, ý đúng", tone(1318.5, 0.9, 0.002, 0.35, (1, 0.25, 0.05)))
    add("bell", "thong-bao", "Chuông nhỏ", "kêu gọi (CTA), nhắc follow", tone(1567.98, 1.2, 0.002, 0.5, (1, 0.5, 0.25, 0.1)) + 0.5 * tone(2349.3, 1.2, 0.002, 0.4))
    n1, n2 = tone(880, 0.25, 0.002, 0.12), tone(1318.5, 0.5, 0.002, 0.2)
    note = np.zeros(int(SR * 0.65))
    note[: len(n1)] += n1
    note[int(SR * 0.13):int(SR * 0.13) + len(n2)] += n2
    add("notify", "thong-bao", "Thông báo 2 nốt", "tin nhắn/khách liên hệ, thông báo app", note)
    s1, s2 = tone(659.25, 0.3, 0.002, 0.15), tone(987.77, 0.6, 0.002, 0.3)
    succ = np.zeros(int(SR * 0.8))
    succ[: len(s1)] += s1
    succ[int(SR * 0.12):int(SR * 0.12) + len(s2)] += s2
    add("success", "thong-bao", "Thành công (2 nốt lên)", "đạt kết quả, chốt deal, tích xanh", succ)
    cash = np.zeros(int(SR * 1.0))
    clk = bp(rng.standard_normal(int(SR * 0.08)), 2000, 9000) * env(int(SR * 0.08), 0.0003, 0.02)
    cash[: len(clk)] += clk
    r1 = tone(2093, 0.7, 0.001, 0.3, (1, 0.6, 0.3)) + tone(2637, 0.7, 0.001, 0.3, (1, 0.4))
    cash[int(SR * 0.1):int(SR * 0.1) + len(r1)] += 0.8 * r1
    add("cash", "thong-bao", "Ka-ching (tiền)", "giá tiền, doanh thu, ưu đãi", cash)
    # --- hiệu ứng ---
    tt = t(1.0)
    sp = sum(np.sin(2 * np.pi * f * tt) * env(len(tt), 0.01 + 0.05 * k, 0.4) for k, f in enumerate([2637, 3136, 3520, 4186, 5274]))
    add("sparkle", "hieu-ung", "Lấp lánh", "chữ sang trọng hiện ra, điểm nổi bật", sp * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * tt) ** 2))
    gl = np.zeros(int(SR * 0.35))
    pos = 0
    while pos < len(gl) - 1200:
        n = int(SR * (0.01 + 0.03 * rng.random()))
        seg = np.sign(np.sin(2 * np.pi * (200 + 2000 * rng.random()) * np.arange(n) / SR)) if rng.random() < 0.5 else bp(rng.standard_normal(n), 500, 6000)
        gl[pos:pos + n] += seg[: len(gl) - pos] * (0.4 + 0.6 * rng.random())
        pos += n
    add("glitch", "hieu-ung", "Nhiễu số (glitch)", "chuyển cảnh công nghệ, lỗi, giật hình", gl)
    sh = np.zeros(int(SR * 0.3))
    for o in (0, int(SR * 0.09)):
        n = int(SR * 0.05)
        sh[o:o + n] += bp(rng.standard_normal(n), 1000, 9000) * env(n, 0.0003, 0.015)
    add("camera", "hieu-ung", "Chụp ảnh (màn trập)", "hiện ảnh minh họa, chụp màn hình", sh)
    tt = t(0.35)
    add("error", "hieu-ung", "Báo sai (rè)", "điều sai lầm, đừng làm vậy, dấu X", np.sign(np.sin(2 * np.pi * 140 * tt)) * 0.6 * env(len(tt), 0.003, 0.25, 1.5))
    (OUT / "sfx.json").write_text(json.dumps(LIB, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(LIB)} hiệu ứng -> {OUT}")


if __name__ == "__main__":
    main()
