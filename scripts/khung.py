"""KHUNG HÌNH (tỉ lệ) của dự án: 9:16 (mặc định) | 4:5 | 1:1 | 16:9 — lưu ở <folder>/khung.json {"format": "1:1"}.
Khung đồ hoạ = khung xuất: 1080×1920 / 1080×1350 / 1080×1080 / 1920×1080. Cỡ chữ / khối giữ nguyên px (khung ngang -> chữ tương đối nhỏ hơn).
y mặc định của các khối tự co theo chiều cao khung; x dạng tỉ lệ 0–1 tự theo bề ngang.
  python scripts/khung.py "<folder>"            -> in khung hiện tại
  python scripts/khung.py "<folder>" 1:1         -> đổi khung (plan.json đã có: dời y các khối theo tỉ lệ)
"""
import json
import sys
from pathlib import Path

FORMATS = {"9:16": (1080, 1920), "4:5": (1080, 1350), "1:1": (1080, 1080), "16:9": (1920, 1080)}
OUT = {"9:16": (1080, 1920), "4:5": (1080, 1350), "1:1": (1080, 1080), "16:9": (1920, 1080)}  # kích thước file xuất
LABEL = {"9:16": "dọc 9:16 (TikTok, Reels, Shorts)", "4:5": "dọc 4:5 (Facebook, Instagram)", "1:1": "vuông 1:1", "16:9": "ngang 16:9 (YouTube)"}


def get(folder: Path) -> str:
    try:
        f = json.loads((Path(folder) / "khung.json").read_text(encoding="utf-8")).get("format")
        return f if f in FORMATS else "9:16"
    except Exception:
        return "9:16"


def height(fmt: str) -> int:
    return FORMATS.get(fmt, FORMATS["9:16"])[1]


def scale_of(fmt: str) -> float:
    """hệ số --scale khi render (hiện mọi khung dựng đúng kích thước xuất -> 1)"""
    return 1.0


def rescale_plan(plan: dict, k: float) -> dict:
    """dời các mốc dọc (px) theo tỉ lệ chiều cao khung mới / cũ"""
    if abs(k - 1) < 1e-6:
        return plan
    for e in plan.get("elements") or []:
        if not e:
            continue
        for key in ("y", "y2", "dy"):
            v = e.get(key)
            # zoom: x / y là tỉ lệ 0–1 (không phải px) -> giữ nguyên
            if isinstance(v, (int, float)) and e.get("type") != "zoom" and not (key != "dy" and 0 <= v <= 1):
                e[key] = round(e[key] * k)
        if isinstance(e.get("org"), list) and len(e["org"]) == 2:
            e["org"] = [e["org"][0], round(e["org"][1] * k)]
        for q in e.get("kf") or []:
            if isinstance(q.get("dy"), (int, float)):
                q["dy"] = round(q["dy"] * k)
        if isinstance(e.get("h"), (int, float)) and e.get("type") in ("pip",) and k < 1:
            e["h"] = round(e["h"] * max(k, 0.55))
    if isinstance(plan.get("captionTop"), (int, float)):
        plan["captionTop"] = round(plan["captionTop"] * k)
    return plan


def set_format(folder: Path, fmt: str, rescale: bool = True) -> dict:
    folder = Path(folder)
    if fmt not in FORMATS:
        raise ValueError("Khung không hợp lệ: " + fmt)
    old = get(folder)
    if fmt == "9:16":
        (folder / "khung.json").unlink(missing_ok=True)
    else:
        (folder / "khung.json").write_text(json.dumps({"format": fmt}), encoding="utf-8")
    pf = folder / "plan.json"
    if rescale and pf.exists() and old != fmt:
        plan = json.loads(pf.read_text(encoding="utf-8"))
        rescale_plan(plan, height(fmt) / height(old))
        pf.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"format": fmt, "old": old}


def auto_fit(vw: float, vh: float, fmt: str) -> str:
    """video chính khác tỉ lệ khung nhiều -> giữ trọn hình + nền mờ ("blur"), gần giống -> cắt cho đầy ("cover")"""
    import math
    if not vw or not vh:
        return "cover"
    fw, fh = OUT[fmt]
    return "blur" if abs(math.log((vw / vh) / (fw / fh))) > 0.32 else "cover"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    f = Path(sys.argv[1]).resolve()
    if len(sys.argv) > 2:
        r = set_format(f, sys.argv[2])
        print(f"Đã đổi khung {r['old']} -> {r['format']} ({LABEL[r['format']]})")
    else:
        g = get(f)
        print(f"Khung: {g} — {LABEL[g]} · khung {OUT[g][0]}×{OUT[g][1]} (y tính trên chiều cao {height(g)}px)")
