"""Cắt bỏ các đoạn thừa / đọc lỗi khỏi video dự án.

Dùng:  python scripts/trim.py "<folder>"

Đọc <folder>/cut.json:  {"cut": [[12.4, 15.0], [33.2, 36.8]]}
  - mốc tính theo _work/transcript_full.txt (video trước khi cắt, đã ghép các clip)
Tạo _work/edit.mp4 và cập nhật words.json / transcript.txt / cuts.json / sheet.jpg / info.json
theo video mới. Luôn cắt lại từ bản đầy đủ, nên sửa cut.json rồi chạy lại thoải mái.
cut rỗng -> quay về bản đầy đủ.
"""
import json
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare import probe, readable, run  # noqa: E402


def merge(cuts, dur):
    cs = sorted([max(0.0, float(a)), min(dur, float(b))] for a, b in cuts if float(b) > float(a))
    out = []
    for a, b in cs:
        if out and a <= out[-1][1] + 0.05:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def main(folder: Path):
    work = folder / "_work"
    info_full = json.loads((work / "info_full.json").read_text(encoding="utf-8"))
    words_full = json.loads((work / "words_full.json").read_text(encoding="utf-8"))
    cuts_full = json.loads((work / "cuts_full.json").read_text(encoding="utf-8"))
    dur = info_full["durationSec"]
    cfg = json.loads((folder / "cut.json").read_text(encoding="utf-8")) if (folder / "cut.json").exists() else {}
    cut = merge(cfg.get("cut", []), dur)

    if not cut:
        for n in ("words", "info", "cuts"):
            (work / f"{n}.json").write_text((work / f"{n}_full.json").read_text(encoding="utf-8"), encoding="utf-8")
        (work / "transcript.txt").write_text((work / "transcript_full.txt").read_text(encoding="utf-8"), encoding="utf-8")
        (work / "edit.mp4").unlink(missing_ok=True)
        print("Không có đoạn cắt — dùng bản đầy đủ.")
        return

    keep, t = [], 0.0
    for a, b in cut:
        if a - t > 0.05:
            keep.append((t, a))
        t = b
    if dur - t > 0.05:
        keep.append((t, dur))

    src = folder / info_full["video"]
    parts = []
    for k, (a, b) in enumerate(keep):
        parts.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{k}];[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[a{k}]")
    fc = ";".join(parts) + ";" + "".join(f"[v{k}][a{k}]" for k in range(len(keep))) + f"concat=n={len(keep)}:v=1:a=1[v][a]"
    out = work / "edit.mp4"
    print(f"Cắt {len(cut)} đoạn, giữ {len(keep)} đoạn...")
    from hw import run_enc
    r = run_enc(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", fc, "-map", "[v]", "-map", "[a]"],
                ["-c:a", "aac", "-ar", "48000"], str(out))
    if r.returncode:
        sys.exit("Lỗi cắt video:\n" + r.stderr[-800:])

    def remap(x):
        """giây ở bản đầy đủ -> giây ở bản đã cắt (None nếu nằm trong đoạn bị cắt)"""
        shift = 0.0
        for a, b in cut:
            if x >= b:
                shift += b - a
            elif x >= a:
                return None
        return round(x - shift, 2)

    words = []
    for w in words_full:
        s = remap(w["start"])
        if s is not None:
            e = remap(min(w["end"], w["start"] + 0.6))
            words.append({**w, "start": s, "end": e if e is not None and e > s else round(s + 0.3, 2)})
    joins, acc = [], 0.0
    for a, b in keep[:-1]:
        acc += b - a
        joins.append(round(acc, 2))
    cuts = sorted({c for c in (remap(c) for c in cuts_full) if c is not None} | set(joins))

    info = {**info_full, **probe(out)}
    info["video"] = "_work/edit.mp4"
    info["clips"] = info_full.get("clips", [])
    info["cutFromFull"] = cut
    d = info["durationSec"]
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-vf", f"fps=16/{d},scale=200:-2,tile=8x2",
         "-frames:v", "1", "-q:v", "4", str(work / "sheet.jpg")])
    (work / "words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    (work / "transcript.txt").write_text(readable(words), encoding="utf-8")
    (work / "cuts.json").write_text(json.dumps(cuts), encoding="utf-8")
    (work / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Xong: {dur}s -> {d}s (bỏ {round(dur - d, 1)}s). Mốc thời gian mới trong transcript.txt")


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    if len(sys.argv) < 2:
        sys.exit('Dùng: python scripts/trim.py "<folder>"')
    from tiendo import wrap
    _f = Path(sys.argv[1]).resolve()
    try:
        _vs = json.loads((_f / "_work" / "info_full.json").read_text(encoding="utf-8"))["durationSec"]
    except Exception:
        _vs = 60
    wrap(_f, "trim", _vs, main, _f, msg="Đang cắt & dựng lại")
