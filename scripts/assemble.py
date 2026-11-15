"""Chế độ VOICE — ghép các cảnh footage theo giọng đọc.

Dùng:  python scripts/assemble.py "<folder>"

Đọc <folder>/canh.json:
  {
   "scenes": [[12.0, 15.5], [40.2, 44.0, 4], [88.0, 92.3, 0.5]],   mốc giây TRONG FOOTAGE (xem _work/footage_*.jpg)
                          số thứ 3 (tuỳ chọn) = TỐC ĐỘ cảnh: 4 = tua nhanh / timelapse (8s footage -> 2s), 0.5 = slow-motion
                          (2s footage -> 4s, tự làm mượt). Độ dài cảnh trên video = (cuối − đầu) / tốc độ. 0.1 … 16
   "origVolume": 0,       tiếng gốc của footage: 0 = tắt (mặc định), 0.15 = nhỏ làm nền
   "musicVolume": 0.12    âm lượng nhạc nền nếu folder có nhac.mp3 (mặc định 0.12)
  }
Các cảnh nối liền nhau từ giây 0 của video. Tổng thời lượng nên ≈ độ dài voice:
thiếu thì giữ khung cuối, thừa thì cắt bớt ở cuối.

Tạo _work/edit.mp4 (1080x1920, 30fps; tiếng = voice [+ nhạc] [+ tiếng gốc]) và cập nhật
info.json / cuts.json / sheet.jpg. words.json / transcript.txt (của voice) giữ nguyên vì cùng mốc thời gian.
Sửa canh.json rồi chạy lại thoải mái.
"""
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare import find_music, find_voice, has_audio, probe, run  # noqa: E402

VF = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p,setsar=1"  # đổi theo khung trong main()
AF = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"


def main(folder: Path):
    work = folder / "_work"
    info = json.loads((work / "info_full.json").read_text(encoding="utf-8"))
    if info.get("mode") != "voice":
        sys.exit("Folder này không ở chế độ voice (chưa có voice.mp3 hoặc chưa chạy prepare.py sau khi thêm voice).")
    voice = find_voice(folder)
    if not voice:
        sys.exit("Không thấy file voice (voice.mp3 / voice.wav / voice.m4a ...) trong folder.")
    global VF
    try:  # khung hình dự án (khung.json)
        import khung
        W, H = khung.OUT[khung.get(folder)]
        VF = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,format=yuv420p,setsar=1"
    except Exception:
        pass
    footage = folder / info["footage"]
    fsec = info["footageSec"]
    vdur = info["durationSec"]

    cfg_file = folder / "canh.json"
    if not cfg_file.exists():
        sys.exit("Chưa có canh.json — xem hướng dẫn ở đầu file scripts/assemble.py")
    cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
    scenes, rates = [], []
    for sc in cfg.get("scenes", []):
        a, b = (sc["from"], sc["to"]) if isinstance(sc, dict) else sc[:2]
        rt = sc.get("speed", 1) if isinstance(sc, dict) else (sc[2] if len(sc) > 2 else 1)
        a, b = max(0.0, float(a)), min(fsec, float(b))
        if b - a >= 0.2:
            scenes.append((a, b))
            rates.append(max(0.1, min(16.0, float(rt or 1))))
    if not scenes:
        sys.exit("canh.json chưa có cảnh hợp lệ (mốc phải nằm trong 0–%ss của footage)." % fsec)
    orig_vol = float(cfg.get("origVolume", 0))
    music_vol = float(cfg.get("musicVolume", 0.12))
    music = find_music(folder)
    total = sum((b - a) / r for (a, b), r in zip(scenes, rates))

    # ---- hình: cắt từng cảnh (đổi tốc độ nếu có), nối lại, giữ khung cuối nếu thiếu, cắt đúng bằng voice ----
    fc = []
    for k, (a, b) in enumerate(scenes):
        r = rates[k]
        if abs(r - 1) < 1e-3:
            fc.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS,{VF}[v{k}]")
        else:  # chậm: nội suy khung cho mượt; nhanh: bỏ bớt khung
            sm = ",minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1" if r < 0.8 and cfg.get("smooth", "mci") == "mci" else \
                 ",framerate=fps=30:interp_start=0:interp_end=255:scene=8" if r < 0.8 else ""
            vf = VF.replace(",fps=30", "")
            fc.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=(PTS-STARTPTS)/{r:.4f},{vf}{sm},fps=30[v{k}]")
    fc.append("".join(f"[v{k}]" for k in range(len(scenes))) + f"concat=n={len(scenes)}:v=1:a=0[vc]")
    pad = max(0.0, vdur - total) + 0.5
    fc.append(f"[vc]tpad=stop_mode=clone:stop_duration={pad:.3f},trim=0:{vdur:.3f},setpts=PTS-STARTPTS[v]")

    # ---- tiếng: voice + (nhạc) + (tiếng gốc) ----
    inputs = ["-i", str(footage), "-i", str(voice)]
    mix = [f"[1:a]{AF},apad,atrim=0:{vdur:.3f}[va]"]
    labels = ["[va]"]
    if music and music_vol > 0:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        fade = max(0.0, vdur - 1.5)
        mix.append(f"[2:a]{AF},atrim=0:{vdur:.3f},volume={music_vol},afade=t=out:st={fade:.3f}:d=1.5[ma]")
        labels.append("[ma]")
    if orig_vol > 0 and has_audio(footage):
        for k, (a, b) in enumerate(scenes):
            r = rates[k]
            if abs(r - 1) < 1e-3:
                mix.append(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,{AF}[o{k}]")
            else:  # cảnh đổi tốc độ: tiếng gốc im lặng (đúng độ dài mới)
                mix.append(f"aevalsrc=0:d={(b - a) / r:.3f}:s=48000,{AF}[o{k}]")
        mix.append("".join(f"[o{k}]" for k in range(len(scenes))) +
                   f"concat=n={len(scenes)}:v=0:a=1,volume={orig_vol},apad,atrim=0:{vdur:.3f}[oa]")
        labels.append("[oa]")
    if len(labels) > 1:
        mix.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:dropout_transition=0:normalize=0[a]")
    else:
        mix[0] = mix[0].replace("[va]", "[a]")

    out = work / "edit.mp4"
    nsp = sum(1 for r in rates if abs(r - 1) > 1e-3)
    print(f"Ghép {len(scenes)} cảnh ({total:.1f}s hình{f', {nsp} cảnh đổi tốc độ' if nsp else ''}) theo voice {vdur}s"
          + (f" + nhạc {music.name}" if music and music_vol > 0 else "")
          + (f" + tiếng gốc {orig_vol}" if orig_vol > 0 else "") + "...")
    from hw import run_enc
    r = run_enc(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc + mix),
                 "-map", "[v]", "-map", "[a]", "-t", f"{vdur:.3f}"], ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"], str(out))
    if r.returncode:
        sys.exit("Lỗi ghép cảnh:\n" + r.stderr[-1200:])

    joins, acc = [], 0.0
    for (a, b), r in zip(scenes[:-1], rates):
        acc += (b - a) / r
        if acc < vdur - 0.3:
            joins.append(round(acc, 2))
    new = {**info, **probe(out)}
    new["video"] = "_work/edit.mp4"
    new["scenes"] = [[round(a, 2), round(b, 2)] + ([r] if abs(r - 1) > 1e-3 else []) for (a, b), r in zip(scenes, rates)]
    d = new["durationSec"]
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-vf", f"fps=16/{d},scale=200:-2,tile=8x2",
         "-frames:v", "1", "-q:v", "4", str(work / "sheet.jpg")])
    (work / "cuts.json").write_text(json.dumps(joins), encoding="utf-8")
    (work / "info.json").write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding="utf-8")
    msg = f"Xong: {out} ({d}s, {len(scenes)} cảnh, {len(joins)} điểm chuyển)."
    if abs(total - vdur) > 1.0:
        msg += f"\n[!] Tổng cảnh {total:.1f}s {'ngắn' if total < vdur else 'dài'} hơn voice {vdur}s " \
               f"— {'đã giữ khung cuối' if total < vdur else 'phần thừa ở cuối bị cắt'}."
    print(msg)


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    if len(sys.argv) < 2:
        sys.exit('Dùng: python scripts/assemble.py "<folder>"')
    from tiendo import wrap, _video_sec
    _f = Path(sys.argv[1]).resolve()
    wrap(_f, "assemble", _video_sec(_f), main, _f, msg="Đang ghép cảnh")
