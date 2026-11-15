"""Tự cắt từ đệm đứng riêng (à, ừ, ờ…) và khoảng lặng dài — KHÔNG cần Claude, không tốn lượt.

    python scripts/cat_lang.py "<folder>" [--gap 0.6] [--khong-tu-dem] [--chay]

Đọc _work/words_full.json (bản trước khi cắt) -> ghi cut.json (mốc theo transcript_full). --chay = chạy luôn trim.py.
Giữ nguyên các mục đã có trong cut.json (gộp thêm). Cùng cách tính với nút "Tự cắt khoảng lặng & từ đệm" của trình chỉnh sửa.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

FILLERS = {"à", "ừ", "ừm", "ừa", "ờ", "ơ", "ơi", "hừm", "hmm", "ầy", "ấy", "ê", "ạ", "ủa", "uhm", "um", "ừng", "dạ"}


def norm(w: str) -> str:
    return re.sub(r"[.,!?…\"“”'()\-:;]", "", str(w).lower()).strip()


def cuts_of(words: list, dur: float, gap: float = 0.6, fillers: bool = True, pad: float = 0.12) -> list:
    ws = sorted(words, key=lambda w: w["start"])
    if not ws:
        return []
    cuts = []
    if fillers:
        keep = []
        for i, w in enumerate(ws):
            prev, nxt = (ws[i - 1] if i else None), (ws[i + 1] if i + 1 < len(ws) else None)
            iso = (not prev or w["start"] - prev["end"] > 0.12) and (not nxt or nxt["start"] - w["end"] > 0.12)
            if norm(w["w"]) in FILLERS and w["end"] - w["start"] < 0.9 and iso:
                cuts.append([max(0.0, w["start"] - 0.03), min(dur, w["end"] + 0.03)])
            else:
                keep.append(w)
        ws = keep
    if not ws:
        return []
    if ws[0]["start"] > gap:
        cuts.append([0.0, max(0.0, ws[0]["start"] - pad)])
    for a, b in zip(ws, ws[1:]):
        if b["start"] - a["end"] > gap:
            cuts.append([a["end"] + pad, b["start"] - pad])
    if dur - ws[-1]["end"] > gap:
        cuts.append([ws[-1]["end"] + pad, dur])
    cuts.sort()
    out = []
    for a, b in cuts:
        if out and a <= out[-1][1] + 0.05:
            out[-1][1] = max(out[-1][1], b)
        elif b - a >= 0.15:
            out.append([a, b])
    return [[round(a, 2), round(b, 2)] for a, b in out]


def main(folder: Path, gap: float, fillers: bool, run_trim: bool):
    work = folder / "_work"
    wf = work / "words_full.json" if (work / "words_full.json").exists() else work / "words.json"
    info_f = work / "info_full.json" if (work / "info_full.json").exists() else work / "info.json"
    words = json.loads(wf.read_text(encoding="utf-8"))
    dur = json.loads(info_f.read_text(encoding="utf-8"))["durationSec"]
    new = cuts_of(words, dur, gap, fillers)
    cf = folder / "cut.json"
    old = json.loads(cf.read_text(encoding="utf-8")).get("cut", []) if cf.exists() else []
    allc = sorted([list(map(float, c)) for c in old] + new)
    merged = []
    for a, b in allc:
        if merged and a <= merged[-1][1] + 0.05:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    cf.write_text(json.dumps({"cut": merged}, ensure_ascii=False), encoding="utf-8")
    sec = sum(b - a for a, b in new)
    print(f"Tự cắt: {len(new)} chỗ (từ đệm + lặng > {gap}s), bớt {sec:.1f}s -> cut.json")
    if run_trim and merged:
        r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "trim.py"), str(folder)])
        sys.exit(r.returncode)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    a = sys.argv
    g = float(a[a.index("--gap") + 1]) if "--gap" in a else 0.6
    main(Path(a[1]).resolve(), g, "--khong-tu-dem" not in a, "--chay" in a)
