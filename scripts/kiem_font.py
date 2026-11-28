"""KIỂM FONT TIẾNG VIỆT cho chữ trong plan.json (khối text, thẻ đồ hoạ, phụ đề) — chat_luong.py tự gọi (dòng "CHUẨN: FONT …").
Ý tưởng từ fontcheck của LumReels (github.com/lumtekvn/lumreels, MIT): đừng tin tên font, mở chính file font ra xem có đủ chữ không.

Bắt: font không có trong thư viện (bộ dựng lặng lẽ thay bằng Be Vietnam Pro) · ký tự font không có (chữ đó rơi sang font khác,
lệch nét giữa chừng — hay gặp với dấu tiếng Việt ở font thư pháp) · chữ nghiêng mà font không có bản nghiêng (trình duyệt nghiêng
giả) · con số viết bằng font thư pháp / viết tay · ký hiệu “₫”.
Chạy riêng: python scripts/kiem_font.py "<folder>"
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NM = ROOT / "node_modules" / "@fontsource"
CACHE = ROOT / "_cache" / "font-cover.json"
SUBSETS = ("latin", "latin-ext", "vietnamese")
DEFAULT = "Be Vietnam Pro"
TEXT_KEYS = ("text", "title", "sub", "label", "value", "price", "note", "question", "name", "caption")


def _lib():
    """{family_lower: {family, id, kind, weights:set, italic:set}} theo remotion/fonts.json + font thật được nạp trong fonts.ts"""
    try:
        fl = json.loads((ROOT / "remotion" / "fonts.json").read_text(encoding="utf-8"))
    except Exception:  # noqa
        return {}
    ts = ""
    try:
        ts = (ROOT / "remotion" / "src" / "fonts.ts").read_text(encoding="utf-8")
    except Exception:  # noqa
        pass
    out = {}
    for f in fl:
        ws = {int(m.group(1)) for m in re.finditer(rf"@fontsource/{re.escape(f['id'])}/(\d{{3}})\.css", ts)} or set(f.get("weights") or [400])
        it = {int(m.group(1)) for m in re.finditer(rf"@fontsource/{re.escape(f['id'])}/(\d{{3}})-italic\.css", ts)}
        out[f["family"].lower()] = {"family": f["family"], "id": f["id"], "kind": f.get("kind", "sans"), "weights": ws, "italic": it}
    return out


def _cover(fid: str, weight: int) -> set:
    """bộ ký tự (mã unicode) font có ở độ đậm gần nhất — đọc thẳng file woff2, nhớ vào _cache"""
    key = f"{fid}:{weight}"
    try:
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:  # noqa
        cache = {}
    if key in cache:
        return set(cache[key])
    try:
        from fontTools.ttLib import TTFont
    except Exception:  # noqa
        return set()
    cps = set()
    for sub in SUBSETS:
        f = NM / fid / "files" / f"{fid}-{sub}-{weight}-normal.woff2"
        if not f.exists():
            continue
        try:
            cps |= set(TTFont(str(f)).getBestCmap().keys())
        except Exception:  # noqa
            pass
    if cps:
        cache[key] = sorted(cps)
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
    return cps


def _emoji(ch: str) -> bool:
    """biểu tượng / emoji (📍 ★ ✓…) — cố ý dùng, hiện bằng font emoji, không tính là thiếu dấu"""
    o = ord(ch)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF or o in (0xFE0F, 0x200D, 0x20E3)


def _nearest(ws, want):
    ws = sorted(ws) or [400]
    return min(ws, key=lambda w: abs(w - want))


def _style(folder: Path) -> dict:
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import phongcach
        return ((phongcach.project_style(folder) or {}).get("style")) or {}
    except Exception:  # noqa
        return {}


def _texts(e: dict):
    for k in TEXT_KEYS:
        v = e.get(k)
        if isinstance(v, str) and v.strip():
            yield v
    for it in e.get("items") or []:
        if isinstance(it, dict):
            for k in TEXT_KEYS:
                if isinstance(it.get(k), str):
                    yield it[k]
        elif isinstance(it, str):
            yield it


def check(folder: Path, plan: dict = None) -> list:
    folder = Path(folder)
    plan = plan or json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    lib = _lib()
    if not lib:
        return []
    st = plan.get("style") or _style(folder)
    tx = st.get("text") or {}
    head = st.get("heading") or st.get("font") or DEFAULT
    body = st.get("font") or DEFAULT
    out, seen = [], set()

    def test(text: str, font: str, weight: int, italic: bool, where: str):
        f = lib.get(str(font).lower())
        if not f:
            k = ("lib", font)
            if k not in seen:
                seen.add(k)
                out.append(f"FONT “{font}” ({where}) không có trong thư viện font của tool — bộ dựng thay bằng {DEFAULT}; "
                           f"chọn font trong remotion/fonts.json hoặc bỏ trường font")
            return
        w = _nearest(f["weights"], int(weight or 400))
        cov = _cover(f["id"], w)
        if cov:
            miss = sorted({ch for ch in text if not ch.isspace() and ord(ch) not in cov and ord(ch) >= 32 and not _emoji(ch)})
            if miss:
                k = ("miss", f["family"], "".join(miss))
                if k not in seen:
                    seen.add(k)
                    out.append(f"FONT {f['family']} {w} thiếu ký tự “{''.join(miss)}” ({where}: “{text[:40]}”) — những chữ đó hiện bằng "
                               f"font khác, lệch nét; đổi font có đủ dấu hoặc viết lại")
        if italic and not f["italic"]:
            k = ("it", f["family"])
            if k not in seen:
                seen.add(k)
                out.append(f"FONT {f['family']} không có bản nghiêng — “italic” ở {where} là nghiêng giả (méo dấu); bỏ italic hoặc đổi font có nghiêng")
        if f["kind"] in ("script", "hand") and re.search(r"\d", text):
            k = ("dig", f["family"], text)
            if k not in seen:
                seen.add(k)
                out.append(f"FONT con số trong “{text[:40]}” ({where}) viết bằng {f['family']} (thư pháp / viết tay) — khó đọc; số / giá để font tiêu đề")
        if "₫" in text and ("dong", 0) not in seen:
            seen.add(("dong", 0))
            out.append(f"FONT ký hiệu “₫” ({where}) nhiều font vẽ lệch — viết “đ” hoặc “VNĐ”")

    for e in plan.get("elements") or []:
        if not e or e.get("hidden"):
            continue
        t = e.get("type")
        where = f"{t} {float(e.get('start', 0)):.1f}s"
        if t == "text":
            font = e.get("font") or tx.get("font") or head
            test(str(e.get("text", "")), font, e.get("weight") or tx.get("weight") or 900, bool(e.get("italic")), where)
        elif t in ("canhAI", "audio", "sfx", "broll", "pip", "fx", "zoom", "solid", "bars", "overlay"):
            continue
        else:
            for s in _texts(e):  # thẻ đồ hoạ: chữ to theo font tiêu đề, chữ nhỏ theo font chữ
                test(s, head, 800, False, where)
                if body != head:
                    test(s, body, 400, False, where)
    cap = plan.get("captions")
    if cap is not False:
        words = []
        if isinstance(cap, list):
            words = [w.get("w", "") for pg in cap for w in (pg or []) if isinstance(w, dict)]
        else:
            try:
                words = [w.get("w", "") for w in json.loads((folder / "_work" / "words.json").read_text(encoding="utf-8")) if isinstance(w, dict)]
            except Exception:  # noqa
                pass
        for fx in plan.get("fixes") or []:
            if isinstance(fx, (list, tuple)) and len(fx) > 1:
                words.append(str(fx[1]))
        if words:
            c = st.get("captions") or {}
            test(" ".join(words), c.get("font") or body, c.get("weight") or 800, False, "phụ đề")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    r = check(Path(sys.argv[1]).resolve())
    print("== Kiểm font tiếng Việt ==")
    print("\n".join("- " + x for x in r) or "- đạt")
