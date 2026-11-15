"""LOGO + SỐ ĐIỆN THOẠI chèn tự động vào video (⚙ Cài đặt → Logo & SĐT).

Lưu ở gốc tool:  thuong-hieu.json  +  thuong-hieu/logo.<đuôi>
  {"logo": "logo.png", "phone": "0912 345 678", "phoneLabel": "Hotline", "applyAll": true,
   "logoPos": "tl|tr|tc|bl|custom", "logoX": 0.5 (tâm ngang 0–1, khi custom), "logoY": 150 (mép trên, px), "logoSize": 170, "logoOpacity": 0.92, "logoWhen": "all|startend|end",
   "phonePos": "under|bottom|top|custom", "phoneX": 0.5 (tâm ngang 0–1, khi custom), "phoneY": 1250 (mép trên, px),
   "phoneSize": 42 (cỡ chữ SĐT, px), "phoneWhen": "all|startend|end", "phoneBg": "#E63946", "phoneColor": "#FFFFFF",
   "endCard": true, "endSec": 4}
Mỗi dự án: <folder>/thuong-hieu.json {"on": true|false} ghi đè (tích / bỏ tích trên trang dự án).
  - applyAll = true  -> mọi dự án có logo/SĐT, trừ dự án đã tắt.
  - applyAll = false -> chỉ dự án đã bật.
plan.json "brandMark": false = tắt riêng cho bản dựng đó; một dict = ghi đè vài thông số (vd {"logoPos": "tr"}).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "thuong-hieu.json"
DIR = ROOT / "thuong-hieu"
DEFAULT = {"logo": "", "phone": "", "phoneLabel": "", "applyAll": True, "logoPos": "tl", "logoX": 0.5, "logoY": 150, "logoSize": 170, "logoOpacity": 0.92,
           "logoWhen": "all", "phonePos": "under", "phoneX": 0.5, "phoneY": 1250, "phoneSize": 42, "phoneWhen": "all", "phoneBg": "#E63946", "phoneColor": "#FFFFFF",
           "endCard": True, "endSec": 4}
KEYS = list(DEFAULT)
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}


def load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    out = {**DEFAULT, **{k: v for k, v in d.items() if k in KEYS}}
    if out["logo"] and not (DIR / out["logo"]).exists():
        out["logo"] = ""
    return out


def save(d: dict) -> dict:
    cur = load()
    for k in KEYS:
        if k in d and k != "logo":
            cur[k] = d[k]
    cur["phone"] = str(cur.get("phone") or "").strip()[:40]
    cur["phoneLabel"] = str(cur.get("phoneLabel") or "").strip()[:40]
    FILE.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
    return cur


def set_logo(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in IMG_EXT:
        raise ValueError("Logo phải là ảnh (png, jpg, webp, svg)")
    DIR.mkdir(exist_ok=True)
    for old in DIR.glob("logo.*"):
        old.unlink()
    name = "logo" + ext
    (DIR / name).write_bytes(data)
    cur = load()
    cur["logo"] = name
    FILE.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
    return name


def remove_logo():
    for old in DIR.glob("logo.*") if DIR.exists() else []:
        old.unlink()
    cur = load()
    cur["logo"] = ""
    FILE.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")


def project_on(folder: Path):
    """True / False nếu dự án đã tích riêng, None = theo cài đặt chung."""
    try:
        v = json.loads((Path(folder) / "thuong-hieu.json").read_text(encoding="utf-8")).get("on")
        return bool(v) if v is not None else None
    except Exception:
        return None


def set_project(folder: Path, on):
    f = Path(folder) / "thuong-hieu.json"
    if on is None:
        f.unlink(missing_ok=True)
    else:
        f.write_text(json.dumps({"on": bool(on)}), encoding="utf-8")


def active(folder: Path) -> bool:
    d = load()
    if not (d["logo"] or d["phone"]):
        return False
    p = project_on(folder)
    return p if p is not None else bool(d["applyAll"])


def mark(folder: Path, plan: dict = None):
    """dict brandMark (logo = đường dẫn TUYỆT ĐỐI) hoặc None nếu không chèn."""
    pb = (plan or {}).get("brandMark")
    if pb is False or not active(folder):
        return None
    d = load()
    m = {k: d[k] for k in KEYS if k not in ("applyAll",)}
    if isinstance(pb, dict):
        m.update({k: v for k, v in pb.items() if k in KEYS and k != "logo"})
    m["logo"] = str(DIR / d["logo"]) if d["logo"] else None
    if not m["logo"]:
        m.pop("logo")
    if not m.get("phone"):
        m.pop("phone", None)
    return m


def note(folder: Path) -> str:
    """1 dòng cho Claude biết video sẽ có logo/SĐT ở đâu (để không đặt chữ đè lên)."""
    m = mark(folder)
    if not m:
        return ""
    pos = {"tl": "góc trên trái", "tr": "góc trên phải", "tc": "giữa phía trên", "bl": "góc dưới trái (y≈1180)"}
    ph = {"under": "dưới logo", "bottom": "giữa, y≈1250 (trên phụ đề)", "top": "giữa phía trên",
          "custom": f"tự đặt: tâm x≈{round(float(m.get('phoneX', 0.5)) * 1080)}px, y≈{int(m.get('phoneY', 1250))}–{int(m.get('phoneY', 1250)) + int(m.get('phoneSize', 42) * 1.8)}px"}
    s = []
    try:
        pl = json.loads((Path(folder) / "plan.json").read_text(encoding="utf-8"))
        if m.get("logoPos") in ("tl", "tc") and any(e and e.get("type") == "dayBadge" for e in pl.get("elements", [])):
            m["logoPos"] = "tr"  # Brand.tsx tự dời khi có nhãn NGÀY X/Y
    except Exception:
        pass
    if m.get("logo"):
        if m.get("logoPos") == "custom":
            w, cx, y = int(m["logoSize"]), round(float(m.get("logoX", 0.5)) * 1080), int(m.get("logoY", 150))
            s.append(f"logo tự đặt: x≈{cx - w // 2}–{cx + w // 2}px, y từ {y}px (rộng {w}px)")
        else:
            s.append(f"logo {pos.get(m['logoPos'], m['logoPos'])} (rộng {m['logoSize']}px)")
    if m.get("phone"):
        s.append(f"SĐT {m['phone']} {ph.get(m['phonePos'], m['phonePos'])}")
    if m.get("endCard"):
        s.append(f"màn kết logo + SĐT {m['endSec']}s cuối")
    return "Logo & SĐT tự chèn khi xuất: " + "; ".join(s) + " — đừng đặt chữ đè chỗ đó; CTA có thể nhắc SĐT."


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(note(Path(sys.argv[1])) or "Dự án này không chèn logo / SĐT.")
    else:
        print(json.dumps(load(), ensure_ascii=False, indent=1))
