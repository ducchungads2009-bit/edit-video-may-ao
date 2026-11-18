"""Tự cắt từ đệm đứng riêng (à, ừ, ờ…) và khoảng lặng dài — KHÔNG cần Claude, không tốn lượt.

    python scripts/cat_lang.py "<folder>" [--gap 0.6] [--khong-tu-dem] [--khong-lap] [--xem] [--chay] [--kiem]
    Tự dò thêm chỗ nói vấp / nói lại (cụm từ lặp lại ngay sau đó -> bỏ lần nói trước); --xem = chỉ in, không ghi; --kiem = soát video ĐÃ cắt (words.json) xem còn lặp / từ đệm không.

Đọc _work/words_full.json (bản trước khi cắt) -> ghi cut.json (mốc theo transcript_full). --chay = chạy luôn trim.py.
Giữ nguyên các mục đã có trong cut.json (gộp thêm). Cùng cách tính với nút "Tự cắt khoảng lặng & từ đệm" của trình chỉnh sửa.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

FILLERS = {"à", "ừ", "ừm", "ừa", "ờ", "ơ", "ơi", "hừm", "hmm", "ầy", "ấy", "ê", "ạ", "ủa", "uhm", "um", "ừng", "dạ"}
# từ đệm "chắc chắn" — cắt cả khi nói liền vào câu; các từ còn lại (ấy, ạ, dạ, ơi, ủa…) có nghĩa nên chỉ cắt khi đứng riêng
STRONG = {"à", "ừ", "ừm", "ừa", "ờ", "ơ", "hừm", "hmm", "ầy", "uhm", "um", "ừng", "ê"}


def repeats_of(ws: list, max_n: int = 6, look: int = 14) -> list:
    """Chỗ nói vấp / nói lại: cụm 2–6 từ lặp lại ngay sau đó (trong ~14 từ) -> cắt lần nói trước (giữ lần sau, thường trọn câu).
    1 từ lặp liền nhau chỉ tính khi giữa 2 lần có ngắt > 0,25s (tránh từ láy: "từ từ", "xinh xinh")."""
    out, i, n_ws = [], 0, len(ws)
    W = [norm(w["w"]) for w in ws]
    while i < n_ws - 1:
        hit = None
        for n in range(min(max_n, (n_ws - i) // 2), 1, -1):
            a = W[i:i + n]
            if not all(a):
                continue
            for j in range(i + n, min(n_ws - n + 1, i + n + look)):
                if W[j:j + n] == a:
                    hit = (j, n); break
            if hit:
                break
        if not hit and W[i] and W[i] == W[i + 1] and ws[i + 1]["start"] - ws[i]["end"] > 0.25:
            hit = (i + 1, 1)
        if hit:
            j, n = hit
            a0, b0 = ws[i]["start"] - 0.03, ws[j]["start"] - 0.05
            if 0.15 < b0 - a0 < 8:
                out.append([round(max(0.0, a0), 2), round(b0, 2), " ".join(w["w"] for w in ws[i:j])])
            i = j
        else:
            i += 1
    return out


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
            nw = norm(w["w"])
            if (nw in STRONG and w["end"] - w["start"] < 0.7) or (nw in FILLERS and w["end"] - w["start"] < 0.9 and iso):
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
    if "--kiem" in sys.argv:  # soát lại SAU khi cắt: còn chỗ lặp / từ đệm nào trong video đã cắt không
        ws = sorted(json.loads((work / "words.json").read_text(encoding="utf-8")), key=lambda w: w["start"])
        rep = repeats_of(ws)
        fil = [w for w in ws if norm(w["w"]) in STRONG]
        for a, b, t in rep:
            print(f"  CÒN lặp {a:.2f}–{b:.2f}s (video đã cắt): “{t}”")
        for w in fil:
            print(f"  CÒN từ đệm “{w['w']}” ở {w['start']:.2f}s")
        print("Sạch — không còn chỗ lặp / từ đệm." if not rep and not fil else f"Còn {len(rep)} chỗ lặp, {len(fil)} từ đệm — thêm vào cut.json (mốc transcript_full) rồi trim lại.")
        return
    wf = work / "words_full.json" if (work / "words_full.json").exists() else work / "words.json"
    info_f = work / "info_full.json" if (work / "info_full.json").exists() else work / "info.json"
    words = json.loads(wf.read_text(encoding="utf-8"))
    dur = json.loads(info_f.read_text(encoding="utf-8"))["durationSec"]
    new = cuts_of(words, dur, gap, fillers)
    rep = [] if "--khong-lap" in sys.argv else repeats_of(sorted(words, key=lambda w: w["start"]))
    for a, b, t in rep:
        print(f"  nói lại / vấp {a:.2f}–{b:.2f}s: bỏ “{t}”")
    new = sorted(new + [[a, b] for a, b, _ in rep])
    if "--xem" in sys.argv:
        print(f"(xem thử) {len(new)} chỗ, bớt {sum(b - a for a, b in new):.1f}s — chưa ghi cut.json"); return
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
    print(f"Tự cắt: {len(new)} chỗ (từ đệm + lặng > {gap}s + nói lại), bớt {sec:.1f}s -> cut.json")
    if run_trim and merged:
        r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "trim.py"), str(folder)])
        sys.exit(r.returncode)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    a = sys.argv
    g = float(a[a.index("--gap") + 1]) if "--gap" in a else 0.6
    main(Path(a[1]).resolve(), g, "--khong-tu-dem" not in a, "--chay" in a)
