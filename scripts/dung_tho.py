"""Lời thoại của bản DỰNG THÔ (người dùng đã tự cắt ghép trong trình chỉnh sửa, plan.json "roughCut": true).

    python scripts/dung_tho.py "<folder>"

Ghi _work/transcript_tho.txt: chỉ những câu còn giữ lại, mốc giây theo VIDEO XUẤT RA (đã cắt) — Claude đọc file này
thay cho transcript_full / clips, không phải tự quy đổi mốc, đỡ tốn lượt.
"""
import json
import sys
from pathlib import Path


def build(folder: Path) -> str:
    work = folder / "_work"
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    words = json.loads((work / "words.json").read_text(encoding="utf-8")) if (work / "words.json").exists() else []
    info = json.loads((work / "info.json").read_text(encoding="utf-8")) if (work / "info.json").exists() else {}
    segs = plan.get("segments") or [[0, info.get("durationSec") or (words[-1]["end"] if words else 0)]]
    out, acc = [], 0.0
    for a, b in segs:
        for w in words:
            m = (w["start"] + w["end"]) / 2
            if a <= m <= b:
                out.append((round(acc + w["start"] - a, 2), round(acc + w["end"] - a, 2), w["w"]))
        acc += b - a
    lines, cur, t0, last = [], [], None, None
    for s, e, w in out:
        if cur and (s - last > 0.5 or str(cur[-1])[-1:] in ".?!"):
            lines.append(f"[{t0:6.2f}] {' '.join(cur)}")
            cur = []
        if not cur:
            t0 = s
        cur.append(w)
        last = e
    if cur:
        lines.append(f"[{t0:6.2f}] {' '.join(cur)}")
    head = (f"# Bản dựng thô: {len(segs)} đoạn, dài {acc:.1f}s — mốc theo video XUẤT RA (đã cắt).\n"
            "# Người dùng đã tự cắt ghép & chọn chuyển cảnh: KHÔNG đổi segments / transition / joinFx.\n")
    txt = head + "\n".join(lines) + "\n"
    (work / "transcript_tho.txt").write_text(txt, encoding="utf-8")
    return txt


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    t = build(Path(sys.argv[1]))
    print(t[:400] + ("…" if len(t) > 400 else ""))
