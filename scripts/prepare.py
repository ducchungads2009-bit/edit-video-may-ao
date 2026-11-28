"""Bước 1 — chuẩn bị 1 folder video (máy tự chạy, không tốn quota).

Dùng:  python scripts/prepare.py "D:/cho-edit/can-ho-01"

Tạo trong <folder>/_work/:
  info.json        thời lượng, kích thước, file video
  words.json       từng chữ + mốc thời gian (nhận giọng tiếng Việt offline)
  transcript.txt   bản chữ dễ đọc, mỗi dòng có mốc giây
  cuts.json        các điểm chuyển cảnh
  sheet.jpg        ảnh ghép 16 khung hình để xem nhanh nội dung
"""
import json
import re
import os
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # tránh lỗi in tiếng Việt trên Windows
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
MODEL_NAME = "sherpa-onnx-zipformer-vi-2025-04-20"
MODEL_DIR = ROOT / "models" / MODEL_NAME
MODEL_URL = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/{MODEL_NAME}.tar.bz2"
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".opus", ".wma"}
VOICE_NAMES = ("voice", "giong-doc", "loi-doc")   # file giọng đọc đặt ở thư mục gốc dự án, vd voice.mp3
MUSIC_NAMES = ("nhac", "music")                   # nhạc nền (không bắt buộc), vd nhac.mp3
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tiendo import Tien  # noqa: E402

TIEN = None          # tiến độ (giao diện hiện thanh % + thời gian còn lại)
SPAN = (0.0, 1.0)    # khoảng % của giai đoạn đang chạy


def span(a, b):
    global SPAN
    SPAN = (a, b)


def tick(f, msg=""):
    if TIEN:
        TIEN.update(SPAN[0] + (SPAN[1] - SPAN[0]) * max(0.0, min(1.0, f)), msg)


FONTS = ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def list_clips(folder: Path) -> list:
    """Các clip của dự án (thư mục gốc + raw/), theo thứ tự trong thu-tu.txt hoặc theo tên file."""
    vids = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT and p.stem != "final"]
    if (folder / "raw").is_dir():
        vids += [p for p in (folder / "raw").iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT]
    vids.sort(key=lambda p: p.name.lower())
    order_file = folder / "thu-tu.txt"
    if order_file.exists():
        order = [l.strip() for l in order_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        rank = {n: i for i, n in enumerate(order)}
        vids.sort(key=lambda p: (rank.get(p.relative_to(folder).as_posix(), 9999), p.name.lower()))
    return vids


def _find_audio(folder: Path, names) -> Path:
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in AUDIO_EXT and p.stem.lower() in names:
            return p
    return None


def find_voice(folder: Path):
    """File giọng đọc riêng (voice.mp3 / giong-doc.wav ...) -> bật chế độ VOICE."""
    return _find_audio(folder, VOICE_NAMES)


def find_music(folder: Path):
    return _find_audio(folder, MUSIC_NAMES)


def audio_duration(p: Path) -> float:
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)])
    return round(float(r.stdout.strip()), 2)


def footage_sheets(video: Path, work: Path, step=3, cols=10, rows=3) -> list:
    """Ảnh lưới khung hình footage, cách nhau `step` giây, có ghi mốc giây -> để chọn cảnh."""
    for old in work.glob("footage_*.jpg"):
        old.unlink()
    # lấy đúng khung tại mỗi mốc (fps= sẽ lấy lệch ~step/2) -> nhãn giây khớp hình
    base = f"select='isnan(prev_selected_t)+gte(t-prev_selected_t\\,{step - 0.02})',scale=180:-2"
    tries = []
    font = next((f for f in FONTS if Path(f).exists()), None)
    if font:
        ff = font.replace(":", "\\:")
        tries.append(base + f",drawtext=fontfile='{ff}':text='%{{eif\\:t\\:d}}s':x=5:y=5:fontsize=24"
                            ":fontcolor=yellow:box=1:boxcolor=black@0.6")
    tries.append(base)
    for vf in tries:
        r = run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vf", f"{vf},tile={cols}x{rows}",
                 "-vsync", "vfr", "-q:v", "4", str(work / "footage_%02d.jpg")])
        if r.returncode == 0 and list(work.glob("footage_*.jpg")):
            break
    sheets = sorted(work.glob("footage_*.jpg"))
    per = cols * rows * step
    lines = [f"Ảnh lưới footage: mỗi ô cách nhau {step}s, đọc từ trái sang phải, trên xuống dưới; "
             f"mỗi ảnh {cols * rows} ô = {per}s. Mốc giây ghi ở góc ô (nếu có)."]
    lines += [f"{p.name}: {k * per}s – {(k + 1) * per}s" for k, p in enumerate(sheets)]
    (work / "footage.txt").write_text("\n".join(lines), encoding="utf-8")
    return sheets


def find_video(folder: Path) -> Path:
    vids = list_clips(folder)
    if not vids:
        sys.exit(f"Không thấy file video trong {folder}")
    return vids[0]


def has_audio(video: Path) -> bool:
    r = run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(video)])
    return bool(r.stdout.strip())


TARGET = [1080, 1920]  # kích thước video ghép = khung hình dự án (khung.json: 9:16 / 4:5 / 1:1 / 16:9), đặt trong main()


def set_target(folder: Path):
    try:
        import khung
        TARGET[:] = list(khung.OUT[khung.get(folder)])
    except Exception:
        TARGET[:] = [1080, 1920]


def normalize(src: Path, dst: Path):
    """Đưa clip về khung dự án (mặc định 1080x1920), 30fps, âm thanh 48kHz. Clip khác tỉ lệ -> nền mờ phía sau."""
    i = probe(src)
    W, H = TARGET
    same = abs(i["width"] / i["height"] - W / H) < 0.06
    if same:
        fc = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,format=yuv420p[v]"
    else:
        fc = (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:5[bg];"
              f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps=30,format=yuv420p[v]")
    audio = has_audio(src)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src)]
    if not audio:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    from hw import run_enc  # mã hóa bằng phần cứng nếu có (nhanh hơn nhiều)
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "0:a:0" if audio else "1:a:0", "-shortest"]
    r = run_enc(cmd, ["-c:a", "aac", "-ar", "48000", "-ac", "2"], str(dst))
    if r.returncode:
        sys.exit("Lỗi chuẩn hóa clip " + src.name + ":\n" + r.stderr[-800:])


def concat_clips(folder: Path, clips: list, work: Path) -> Path:
    print(f"Ghép {len(clips)} clip theo thứ tự: " + ", ".join(c.name for c in clips))
    parts, bounds, t = [], [], 0.0
    # chuẩn hóa nhiều clip cùng lúc (song song)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from hw import cores
    done = [0]
    with ThreadPoolExecutor(max_workers=max(1, min(len(clips), 4, cores() // 2 or 1))) as ex:
        futs = [ex.submit(normalize, c, work / f"_part{k}.mp4") for k, c in enumerate(clips)]
        for fu in as_completed(futs):
            fu.result()
            done[0] += 1
            tick(done[0] / len(clips), f"Chuẩn hóa clip {done[0]}/{len(clips)}")
    for k, c in enumerate(clips):
        part = work / f"_part{k}.mp4"
        d = probe(part)["durationSec"]
        bounds.append({"file": c.relative_to(folder).as_posix(), "start": round(t, 2), "end": round(t + d, 2)})
        t += d
        parts.append(part)
    lst = work / "_list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    out = work / "ghep.mp4"
    r = run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])
    if r.returncode:
        sys.exit("Lỗi ghép clip:\n" + r.stderr[-800:])
    # Ghép -c copy để lại "lỗ" trong tiếng (mẫu đệm AAC của từng clip bị bỏ khi giải mã tuần tự) -> tiếng giải mã liền
    # bị NGẮN hơn hình (~0,1 s/clip, có video lệch 0,6 s). Mã hóa lại riêng tiếng, lấp lỗ theo mốc thời gian (hình giữ nguyên).
    fixed = work / "_ghep_fix.mp4"
    r2 = run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "copy",
              "-af", "aresample=async=1:first_pts=0", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(fixed)])
    if r2.returncode == 0 and fixed.exists():
        fixed.replace(out)
    else:
        print("[!] Không chuẩn hóa được tiếng sau khi ghép:", (r2.stderr or "")[-300:])
        fixed.unlink(missing_ok=True)
    for p in parts:
        p.unlink()
    lst.unlink()
    (work / "clips.json").write_text(json.dumps(bounds, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def probe(video: Path) -> dict:
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams",
             "-show_entries", "format=duration", "-of", "json", str(video)])
    d = json.loads(r.stdout)
    st = d["streams"][0]
    w, h = st["width"], st["height"]
    # clip điện thoại quay dọc thường lưu ngang + cờ xoay 90° -> đổi lại cho đúng
    rot = st.get("tags", {}).get("rotate")
    for sd in st.get("side_data_list", []):
        if "rotation" in sd:
            rot = sd["rotation"]
    if rot is not None and abs(int(float(rot))) % 180 == 90:
        w, h = h, w
    return {"video": video.name, "durationSec": round(float(d["format"]["duration"]), 2),
            "width": w, "height": h}


def ensure_model():
    if (MODEL_DIR / "tokens.txt").exists():
        return
    print("Tải mô hình nhận giọng tiếng Việt (lần đầu, ~70MB)...")
    MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
    tmp = MODEL_DIR.parent / "model.tar.bz2"
    urllib.request.urlretrieve(MODEL_URL, tmp)
    with tarfile.open(tmp, "r:bz2") as t:
        t.extractall(MODEL_DIR.parent)
    tmp.unlink()


def transcribe(wav: Path) -> list:
    import numpy as np
    import sherpa_onnx
    import soundfile as sf

    ensure_model()
    m = MODEL_DIR
    enc = next(m.glob("encoder-*.onnx")); dec = next(m.glob("decoder-*.onnx")); joi = next(m.glob("joiner-*.onnx"))
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(enc), decoder=str(dec), joiner=str(joi), tokens=str(m / "tokens.txt"), num_threads=min(8, max(2, (os.cpu_count() or 4) - 1)))
    audio, sr = sf.read(str(wav), dtype="float32")
    chunk, words, pos = 15 * sr, [], 0
    while pos < len(audio):
        end = min(pos + chunk, len(audio))
        if end < len(audio):  # cắt ở chỗ nhỏ tiếng nhất trong 2s cuối
            win = audio[end - 2 * sr:end]
            fr = 400
            energy = [np.abs(win[i:i + fr]).mean() for i in range(0, len(win) - fr, fr)]
            end = end - 2 * sr + int(np.argmin(energy)) * fr
        tick(pos / len(audio), f"Nhận giọng {int(pos / sr)}/{int(len(audio) / sr)} giây")
        s = rec.create_stream()
        s.accept_waveform(sr, audio[pos:end])
        rec.decode_stream(s)
        off, cur = pos / sr, None
        for tok, t in zip(s.result.tokens, s.result.timestamps):
            if tok.startswith((" ", "▁")) or cur is None:
                if cur:
                    words.append(cur)
                cur = {"w": tok.strip().lstrip("▁"), "start": round(off + t, 2)}
            else:
                cur["w"] += tok
        if cur:
            words.append(cur)
        pos = end
    words = [w for w in words if w["w"]]
    for i, w in enumerate(words):
        nxt = words[i + 1]["start"] if i + 1 < len(words) else w["start"] + 0.5
        w["end"] = round(min(nxt, w["start"] + 0.6), 2)
    return words


def readable(words: list) -> str:
    lines, cur, t0 = [], [], None
    for i, w in enumerate(words):
        if not cur:
            t0 = w["start"]
        cur.append(w["w"])
        gap = words[i + 1]["start"] - w["start"] if i + 1 < len(words) else 9
        if gap > 0.7 or len(cur) >= 14:
            lines.append(f"[{t0:6.2f}] " + " ".join(cur))
            cur = []
    if cur:
        lines.append(f"[{t0:6.2f}] " + " ".join(cur))
    return "\n".join(lines)


def scene_cuts(video: Path) -> list:
    r = run(["ffmpeg", "-hide_banner", "-i", str(video), "-an", "-vf",
             "scale=270:-2,select='gt(scene,0.3)',showinfo", "-f", "null", "-"])
    cuts = []
    for line in r.stderr.splitlines():
        if "pts_time:" in line:
            t = float(line.split("pts_time:")[1].split()[0])
            if not cuts or t - cuts[-1] > 1.0:
                cuts.append(round(t, 2))
    return cuts


def analyze(folder: Path, video: Path, extra_cuts=()):
    """Nhận giọng + dò chuyển cảnh + ảnh xem nhanh cho 1 file video (dùng chung cho prepare & trim)."""
    work = folder / "_work"
    info = probe(video)
    info["video"] = video.relative_to(folder).as_posix()
    wav = work / "audio.wav"
    wav.unlink(missing_ok=True)
    r = run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-af", "aresample=async=1:first_pts=0", "-ac", "1", "-ar", "16000", str(wav)])
    no_audio = r.returncode != 0 or not wav.exists() or wav.stat().st_size < 1000
    if no_audio:  # video không có tiếng (clip câm, quay màn hình...) -> bỏ qua nhận giọng, vẫn dò cảnh / ảnh xem nhanh
        print("[!] Video không có tiếng (hoặc không đọc được tiếng) — bỏ qua nhận giọng. Muốn có lời: thêm voice (Giọng đọc).", flush=True)
    print("Đang nhận giọng + dò chuyển cảnh (song song)...")
    d = info["durationSec"]

    def side():  # chạy cùng lúc với nhận giọng: dò chuyển cảnh + ảnh xem nhanh + dò mặt (để xếp chữ tránh mặt)
        c = scene_cuts(video)
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vf",
             f"fps=16/{d},scale=200:-2,tile=8x2", "-frames:v", "1", "-q:v", "4", str(work / "sheet.jpg")])
        try:
            import mat
            faces = mat.smooth(mat.detect(video, d))
            hit = [f for f in faces if len(f) == 5]
            big = sum(1 for f in hit if f[3] * f[4] > 1080 * 1920 * 0.035) / max(1, len(faces))
            (work / "mat.json").write_text(json.dumps({"step": mat.STEP, "w": 1080, "h": 1920, "faces": faces, "big": round(big, 2)}), encoding="utf-8")
        except Exception as e:  # noqa
            print("[!] Không dò được mặt (bỏ qua):", e)
        return c
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(side)
        a, b = SPAN
        span(a, a + (b - a) * 0.9)
        words = [] if no_audio else transcribe(wav)
        wav.unlink(missing_ok=True)
        span(a, b)
        tick(0.9, "Dò chuyển cảnh")
        sc = fut.result()
    cuts = sorted(set(sc) | {round(c, 2) for c in extra_cuts if 0.5 < c < info["durationSec"] - 0.5})
    tick(0.98, "Xong phân tích")
    return info, words, cuts


def save_analysis(work: Path, info, words, cuts):
    (work / "words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    (work / "transcript.txt").write_text(readable(words), encoding="utf-8")
    (work / "cuts.json").write_text(json.dumps(cuts), encoding="utf-8")
    (work / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")


def main(folder: Path):
    work = folder / "_work"
    work.mkdir(exist_ok=True)
    set_target(folder)
    clips = list_clips(folder)
    if not clips and find_voice(folder):  # CHỈ TIẾNG: chỉ có giọng đọc, không video -> nền giấy + chữ + tranh minh họa
        return main_audio(folder, work, find_voice(folder))
    if not clips:
        sys.exit(f"Không thấy file video trong {folder}")
    (work / "clips.json").unlink(missing_ok=True)
    (work / "edit.mp4").unlink(missing_ok=True)
    global TIEN
    total = 0.0
    for c in clips:
        try:
            total += probe(c)["durationSec"]
        except Exception:
            pass
    TIEN = Tien(folder, "prepare", total)
    TIEN.clock("Đang chuẩn bị")  # % chạy theo thời gian dự kiến, các bước thật sẽ đẩy lên khi xong
    try:
        _main(folder, work, clips)
    except BaseException:
        TIEN.done(False)
        raise
    TIEN.done(True)


def _main(folder: Path, work: Path, clips: list):
    if len(clips) > 1:
        span(0.0, 0.3)
        video = concat_clips(folder, clips, work)
        span(0.3, 1.0)
        joins = [b["start"] for b in json.loads((work / "clips.json").read_text(encoding="utf-8"))[1:]]
    else:
        (work / "ghep.mp4").unlink(missing_ok=True)
        video, joins = clips[0], []
    voice = find_voice(folder)
    if voice:
        return prepare_voice(folder, work, video, clips, joins, voice)
    for old in list(work.glob("footage_*.jpg")) + [work / "footage.txt", work / "footage_cuts.json"]:
        old.unlink(missing_ok=True)
    info, words, cuts = analyze(folder, video, joins)
    info["clips"] = [c.relative_to(folder).as_posix() for c in clips]
    print(f"Video: {info['video']}  {info['durationSec']}s  {info['width']}x{info['height']}")
    save_analysis(work, info, words, cuts)
    # bản gốc (trước khi cắt) để trim.py luôn cắt lại từ đầu
    for n in ("words", "transcript", "info"):
        src = work / (n + (".txt" if n == "transcript" else ".json"))
        (work / (n + "_full" + src.suffix)).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    (work / "cuts_full.json").write_text(json.dumps(cuts), encoding="utf-8")
    print(f"Xong: {len(words)} chữ, {len(cuts)} điểm chuyển cảnh -> {work}")



def prepare_voice(folder: Path, work: Path, footage: Path, clips: list, joins: list, voice: Path):
    """Chế độ VOICE: lời nói lấy từ file voice; footage chỉ dùng làm hình (chọn cảnh bằng canh.json)."""
    print(f"Chế độ VOICE — giọng đọc: {voice.name}")
    (work / "edit.mp4").unlink(missing_ok=True)
    finfo = probe(footage)
    wav = work / "audio.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(voice), "-af", "aresample=async=1:first_pts=0", "-ac", "1", "-ar", "16000", str(wav)])
    print("Đang nhận giọng từ voice...")
    a, b = SPAN
    span(a, a + (b - a) * 0.6)
    words = transcribe(wav)
    wav.unlink(missing_ok=True)
    span(a, b)
    tick(0.6, "Dò chuyển cảnh footage")
    print("Dò chuyển cảnh footage...")
    fd = finfo["durationSec"]
    fcuts = sorted(set(scene_cuts(footage)) | {round(c, 2) for c in joins if 0.5 < c < fd - 0.5})
    print("Tạo ảnh lưới footage...")
    tick(0.8, "Tạo ảnh lưới footage")
    sheets = footage_sheets(footage, work)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(footage), "-vf",
         f"fps=16/{fd},scale=200:-2,tile=8x2", "-frames:v", "1", "-q:v", "4", str(work / "sheet.jpg")])
    music = find_music(folder)
    rel = footage.relative_to(folder).as_posix()
    info = {"mode": "voice", "voice": voice.name, "music": music.name if music else None,
            "video": rel, "footage": rel, "footageSec": fd, "durationSec": audio_duration(voice),
            "width": finfo["width"], "height": finfo["height"],
            "clips": [c.relative_to(folder).as_posix() for c in clips]}
    (work / "footage_cuts.json").write_text(json.dumps(fcuts), encoding="utf-8")
    save_analysis(work, info, words, [])
    for n in ("words", "transcript", "info"):
        src = work / (n + (".txt" if n == "transcript" else ".json"))
        (work / (n + "_full" + src.suffix)).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    (work / "cuts_full.json").write_text("[]", encoding="utf-8")
    print(f"Xong: voice {info['durationSec']}s, {len(words)} chữ; footage {fd}s, {len(sheets)} ảnh lưới -> {work}")
    print("Tiếp theo: viết canh.json rồi chạy scripts/assemble.py")


def main_audio(folder: Path, work: Path, voice: Path):
    """Chế độ CHỈ TIẾNG: không có video, chỉ voice.* (+ nhac.*) -> tạo video nền màu giấy dài đúng bằng voice (tiếng = voice) rồi
    nhận giọng như bình thường. Hình do phong cách vẽ (vd tranh thủy mặc: style.backdrop) + chữ + ảnh minh họa (broll ảnh)."""
    global TIEN
    d = audio_duration(voice)
    TIEN = Tien(folder, "prepare", d)
    TIEN.clock("Tạo nền cho video chỉ có tiếng")
    try:
        (work / "clips.json").unlink(missing_ok=True)
        (work / "ghep.mp4").unlink(missing_ok=True)
        out = work / "chi-tieng.mp4"
        nen = "0xEFE9DC"  # màu giấy; video không clip (video_ai.py) đặt màu nền riêng trong video-ai.json
        try:
            c = json.loads((folder / "video-ai.json").read_text(encoding="utf-8")).get("nen") or ""
            if re.fullmatch(r"#?[0-9A-Fa-f]{6}", c):
                nen = "0x" + c.lstrip("#")
        except Exception:  # noqa
            pass
        r = run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={nen}:s={TARGET[0]}x{TARGET[1]}:r=30:d={d:.3f}", "-i", str(voice),
                 "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                 "-af", "aresample=async=1:first_pts=0", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", str(out)])
        if r.returncode:
            sys.exit("Không tạo được video nền:\n" + r.stderr[-600:])
        info, words, cuts = analyze(folder, out)
        info["mode"] = "audio"
        info["voice"] = voice.name
        music = find_music(folder)
        info["music"] = music.name if music else None
        info["clips"] = []
        save_analysis(work, info, words, [])
        for n in ("words", "transcript", "info"):
            src = work / (n + (".txt" if n == "transcript" else ".json"))
            (work / (n + "_full" + src.suffix)).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        (work / "cuts_full.json").write_text("[]", encoding="utf-8")
        print(f"Xong CHỈ TIẾNG: voice {info['durationSec']}s, {len(words)} chữ -> {work}")
    except BaseException:
        TIEN.done(False)
        raise
    TIEN.done(True)


def speech_chunks(video: Path, d: float) -> list:
    """các khúc có tiếng nói (bù của khoảng lặng ffmpeg silencedetect) -> [{"w": "…", start, end}] để trình chỉnh sửa tự cắt lặng
    khi chưa nhận giọng (chế độ dựng thô)."""
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vn", "-af", "silencedetect=noise=-33dB:d=0.25", "-f", "null", "-"])
    sil, st = [], None
    for line in (r.stderr or "").splitlines():
        if "silence_start:" in line:
            st = float(line.split("silence_start:")[1].split()[0])
        elif "silence_end:" in line and st is not None:
            sil.append((max(0.0, st), float(line.split("silence_end:")[1].split()[0])))
            st = None
    if st is not None:
        sil.append((st, d))
    out, t = [], 0.0
    for a, b in sil:
        if a - t > 0.08:
            out.append({"w": "…", "start": round(t, 2), "end": round(a, 2)})
        t = b
    if d - t > 0.08:
        out.append({"w": "…", "start": round(t, 2), "end": round(d, 2)})
    return out


def main_tho(folder: Path):
    """DỰNG THÔ trước khi chuẩn bị: chỉ chuẩn hóa + ghép các clip (không nhận giọng, không phụ đề, không dò mặt) để người dùng
    cắt ghép / chuyển cảnh trong trình chỉnh sửa; xong bấm "Xong dựng thô" -> xuất bản thô rồi mới Chuẩn bị đầy đủ (xong_tho.py)."""
    work = folder / "_work"
    work.mkdir(exist_ok=True)
    set_target(folder)
    clips = list_clips(folder)
    if not clips:
        sys.exit(f"Không thấy file video trong {folder}")
    global TIEN
    total = sum(probe(c)["durationSec"] for c in clips)
    TIEN = Tien(folder, "prepare", total * 0.4)
    TIEN.clock("Ghép các clip để dựng thô")
    try:
        (work / "clips.json").unlink(missing_ok=True)
        if len(clips) > 1:
            span(0.0, 0.85)
            video = concat_clips(folder, clips, work)
            joins = [b["start"] for b in json.loads((work / "clips.json").read_text(encoding="utf-8"))[1:]]
        else:
            video, joins = clips[0], []
        info = probe(video)
        info["video"] = video.relative_to(folder).as_posix()
        info["clips"] = [c.relative_to(folder).as_posix() for c in clips]
        info["tho"] = True
        tick(0.9, "Dò khoảng lặng")
        (work / "noi.json").write_text(json.dumps(speech_chunks(video, info["durationSec"])), encoding="utf-8")
        save_analysis(work, info, [], [round(j, 2) for j in joins])
        print(f"Xong ghép để DỰNG THÔ: {len(clips)} clip, {info['durationSec']}s -> mở trình chỉnh sửa, tab Dựng thô")
    except BaseException:
        TIEN.done(False)
        raise
    TIEN.done(True)


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    if len(sys.argv) < 2:
        sys.exit('Dùng: python scripts/prepare.py "<folder video>" [--tho]')
    if "--tho" in sys.argv:
        main_tho(Path(sys.argv[1]).resolve())
    else:
        main(Path(sys.argv[1]).resolve())
