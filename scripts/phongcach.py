"""Bộ PHONG CÁCH dùng lại (lấy từ video mẫu).

  phong-cach/<tên>/phong-cach.json   {"ten", "mo_ta", "nguon", "style": {...}, "plan": {...mặc định cho plan.json}}
  phong-cach/<tên>/ghi-chu.md        cách dựng (Claude viết): hook, nhịp chữ, minh họa, âm thanh...
  phong-cach/<tên>/mau.jpg           1 khung hình nét từ video mẫu
  phong-cach/<tên>/demo.jpg          ảnh minh họa tool dựng theo phong cách (tiêu đề, chữ, nhãn dán, phụ đề)
Dự án chọn phong cách: <folder>/phong-cach-tron.json = TỪNG THÀNH PHẦN lấy từ bộ nào, vd
  {"chu": "Kiến thức trắng xanh", "phude": "Chữ đỏ nền khối", "chuyencanh": "_mau"}   ("_mau" = video mẫu của dự án)
(cũ: phong-cach.txt = 1 bộ cho mọi thành phần). render.py tự trộn vào plan.

Dùng:
  python scripts/phongcach.py ds                          liệt kê
  python scripts/phongcach.py xem "<tên>"                 in phong-cach.json + ghi-chu.md
  python scripts/phongcach.py chon "<folder>" "<tên>"     dự án dùng phong cách này cho mọi thành phần ("" = bỏ chọn)
  python scripts/phongcach.py tron "<folder>"              in phong cách đã trộn của dự án (từng thành phần lấy từ đâu + mô tả)
  python scripts/phongcach.py luu "<folder>" "<tên>"      lưu <folder>/_mau/phong-cach.json (+ghi-chu.md) thành bộ phong cách
  python scripts/phongcach.py anh "<tên>"                 vẽ lại ảnh minh họa demo.jpg (sau khi sửa phong-cach.json)
"""
import json
import re
import shutil
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "phong-cach"


def slug(name: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]+', "", name).strip().strip(".")
    return s[:60] or "phong-cach"


# Thành phần của một phong cách: tên, nhãn, các khoá trong "style" và trong "plan"
COMPONENTS = [
    ("chu", "Chữ & font", ["font", "heading", "text"], []),
    ("phude", "Phụ đề", ["captions"], ["captionTop", "wordsPerPage", "captionSize", "captionUpper"]),
    ("chuyencanh", "Chuyển cảnh", [], ["transition", "cutFx"]),
    ("hieuung", "Hiệu ứng (zoom, chớp, rung, lớp phủ, chuyển động)", ["effects", "motion"], []),
    ("dohoa", "Đồ họa & nhãn dán", ["templates", "graphics", "skin", "accent", "frame", "map", "mapTour", "presenter", "backdrop"], ["theme"]),
    ("bocuc", "Bố cục / cách trình bày", ["layout"], []),
    ("icon", "Cách chọn icon", ["icons"], []),
    ("minhhoa", "Chèn ảnh / video minh họa", ["broll"], []),
    ("amthanh", "Âm thanh (sfx, nhạc)", ["sfx"], ["sfxVolume", "musicVolume"]),
    ("mau", "Màu video", [], ["color"]),
    ("nhip", "Nhịp dựng", ["pace", "beat"], []),  # beat = kiểu dựng theo nhịp nhạc {"preset": "trailer"} hoặc học từ mẫu {"ramp", ...}
]
COMP_IDS = [c[0] for c in COMPONENTS]


def extract(preset: dict, comp: str) -> dict:
    """phần của bộ phong cách thuộc 1 thành phần -> {"style": {...}, "plan": {...}}"""
    c = next(x for x in COMPONENTS if x[0] == comp)
    st, pl = preset.get("style") or {}, dict(preset.get("plan") or {})
    if isinstance(pl.get("music"), dict) and "volume" in pl["music"] and "musicVolume" not in pl:
        pl["musicVolume"] = pl["music"]["volume"]
    return {"style": {k: st[k] for k in c[2] if k in st}, "plan": {k: pl[k] for k in c[3] if k in pl}}


LOOK = {"plain": "chữ viền", "outline": "viền đen dày", "clean": "chữ trơn + bóng", "shadow": "bóng đổ cứng", "solid": "nền khối màu",
        "highlight": "bút dạ quang", "neon": "phát sáng", "box": "khung kính", "gold": "chữ vàng 3D", "tag": "nhãn vàng"}
ANIM = {"pop": "bật ra", "bounce": "nảy", "fade": "hiện dần", "up": "trượt lên", "down": "trượt xuống", "left": "trượt ngang",
        "right": "trượt ngang", "blur": "mờ→nét", "zoomOut": "thu nhỏ vào", "wipe": "quét", "type": "gõ từng chữ", "words": "bật từng từ",
        "stagger": "bật từng ký tự", "wave": "sóng lượn", "flip3d": "lật 3D từng chữ", "maskUp": "trồi lên từ khe", "rise": "nổi lên mờ→nét",
        "typeCursor": "gõ + con trỏ", "glitch": "nhiễu glitch", "scramble": "xáo chữ giải mã"}
CAP = {"tiktok": "kiểu TikTok", "karaoke": "karaoke", "box": "nền tối cả dòng", "wordbox": "từ đang đọc có nền", "pop": "bật từng từ",
       "single": "1 từ to mỗi lần", "minimal": "tối giản", "outline": "viền đen dày"}
TRN = {"auto": "tự động (zoom cut / mờ chồng)", "cut": "cắt thẳng", "zoom": "zoom cut", "fade": "mờ chồng", "flash": "chớp sáng",
       "whip": "lia nhanh", "slide": "đẩy ngang", "up": "đẩy lên", "zoomin": "zoom xuyên", "blur": "nhòe chồng"}


def auto_desc(preset: dict, comp: str) -> str:
    """mô tả ngắn 1 thành phần từ thông số (khi bộ phong cách chưa có mô tả)"""
    x = extract(preset, comp)
    st, pl = x["style"], x["plan"]
    parts = []
    if comp == "chu":
        t = st.get("text") or {}
        parts = [st.get("heading") or st.get("font"), LOOK.get(t.get("look")), ANIM.get(t.get("anim")) and "hiện " + ANIM[t["anim"]],
                 t.get("upper") and "viết hoa"]
    elif comp == "phude":
        c = st.get("captions") or {}
        parts = [CAP.get(c.get("preset")), c.get("font"), pl.get("wordsPerPage") and f"{pl['wordsPerPage']} chữ/dòng"]
    elif comp == "chuyencanh":
        parts = [TRN.get(pl.get("transition")), pl.get("cutFx") and pl["cutFx"] != "none" and f"thêm {pl['cutFx']} ở chỗ đổi cảnh"]
    elif comp == "minhhoa":
        b = st.get("broll") or {}
        parts = [b.get("enter") and "ảnh trám vào: " + {"zoom": "phóng to", "slide": "trượt", "up": "trượt lên", "fade": "mờ dần",
                 "cut": "cắt thẳng", "whip": "lia nhanh", "circle": "mở tròn"}.get(b["enter"], b["enter"]),
                 b.get("area") in ("top", "bottom") and ("ảnh trám nửa " + ("trên" if b["area"] == "top" else "dưới") + ", mép hoà trộn"),
                 b.get("pip") and "khung nổi " + {"card3d": "thẻ 3D", "clean": "bo góc viền trắng", "round": "tròn", "polaroid": "polaroid"}.get(b["pip"], b["pip"])]
    elif comp == "mau":
        c = pl.get("color") or {}
        w = c.get("warmth", 0)
        parts = [c.get("brightness", 100) > 102 and "sáng hơn", c.get("brightness", 100) < 98 and "tối hơn",
                 c.get("saturation", 100) > 104 and "rực hơn", c.get("saturation", 100) < 96 and "nhạt màu",
                 c.get("contrast", 100) > 104 and "tương phản cao", c.get("contrast", 100) < 96 and "tương phản dịu",
                 w > 3 and "ấm", w < -3 and "lạnh"]
    elif comp == "amthanh":
        f = st.get("sfx") or {}
        parts = [f.get("density") and {"it": "ít", "vua": "vừa", "nhieu": "nhiều"}[f["density"]] + " hiệu ứng âm thanh",
                 pl.get("sfxVolume") is not None and f"âm lượng sfx {int(pl['sfxVolume'] * 100)}%",
                 pl.get("musicVolume") is not None and f"nhạc nền {int(pl['musicVolume'] * 100)}%"]
    elif comp == "dohoa":
        parts = [st.get("templates") is False and "không dùng thẻ 3D có sẵn", (st.get("graphics") or {}).get("sticker") and
                 "nhãn dán: " + str(st["graphics"]["sticker"])]
    elif comp == "bocuc":
        l = st.get("layout") or {}
        parts = [l.get("align") and "chữ căn " + {"center": "giữa", "left": "trái", "right": "phải"}.get(l["align"], l["align"]),
                 l.get("textZone") and "hay đặt vùng " + {"top": "trên", "middle": "giữa", "bottom": "dưới"}.get(l["textZone"], l["textZone"]),
                 l.get("maxBlocks") and f"tối đa {l['maxBlocks']} khối cùng lúc",
                 l.get("iconPos") and l["iconPos"] != "none" and "icon bên " + {"left": "trái", "right": "phải", "above": "trên", "below": "dưới"}.get(l["iconPos"], "") + " chữ"]
    elif comp == "icon":
        i = st.get("icons") or {}
        parts = [{"emoji": "emoji", "lucide": "icon nét", "filled": "icon đặc", "none": "không dùng icon"}.get(i.get("kind"), i.get("kind")),
                 i.get("bg") and i["bg"] != "none" and "có nền " + {"circle": "tròn", "badge": "huy hiệu 3D", "square": "vuông bo"}.get(i["bg"], i["bg"]),
                 i.get("set") and "hay dùng: " + " ".join(i["set"][:6])]
    elif comp == "hieuung":
        e = st.get("effects") or {}
        parts = [e.get("zoom") and f"zoom {e['zoom']}", e.get("flash") and f"{e['flash']} lần chớp", e.get("shake") and "có rung", e.get("zoomEase") == "smooth" and "zoom vào–ra êm, không giật", e.get("shots") == "auto" and "tự đổi cỡ cảnh toàn–trung–cận",
                 isinstance(e.get("overlay"), list) and "lớp phủ: " + ", ".join(e["overlay"]), (st.get("motion") or {}).get("ease") and f"chuyển động {(st.get('motion') or {})['ease']}",
                 (st.get("motion") or {}).get("mblur") and "nhòe chuyển động"]
    elif comp == "nhip":
        pc = st.get("pace") or {}
        parts = [pc.get("doDaiCanhTB") and f"cảnh ~{pc['doDaiCanhTB']}s", pc.get("chuHinhMoi10s") and f"{pc['chuHinhMoi10s']} lần chữ/hình mỗi 10s"]
    return ", ".join(str(p) for p in parts if p)


def descs(preset: dict) -> dict:
    tp = dict(preset.get("thanhPhan") or {})
    for c in COMP_IDS:
        if not tp.get(c):
            d = auto_desc(preset, c)
            if d:
                tp[c] = d
    return tp


def has_comp(preset: dict, comp: str) -> bool:
    x = extract(preset, comp)
    return bool(x["style"] or x["plan"] or (preset.get("thanhPhan") or {}).get(comp))


def mau_style(folder: Path):
    """phong cách rút từ video mẫu của dự án: Claude ghi (_mau/phong-cach.json) + máy gợi ý (phân tích)"""
    out = {}
    g = folder / "_mau" / "_phan-tich" / "phan-tich.json"
    try:
        out = json.loads(g.read_text(encoding="utf-8")).get("goiY") or {}
    except Exception:
        pass
    f = folder / "_mau" / "phong-cach.json"
    if f.exists():
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
            tp = {**(out.get("thanhPhan") or {}), **(j.get("thanhPhan") or {})}
            out = {**j, "style": _merge(out.get("style") or {}, j.get("style") or {}),
                   "plan": _merge(out.get("plan") or {}, j.get("plan") or {}), "thanhPhan": tp}
        except Exception:
            pass
    if out:
        out.setdefault("ten", "Video mẫu của dự án")
    return out or None


def source(folder: Path, name: str):
    return mau_style(folder) if name == "_mau" else load(name)


def mix_of(folder: Path) -> dict:
    """{thành phần: nguồn} của dự án ('' / thiếu = mặc định)"""
    f = folder / "phong-cach-tron.json"
    has_mau = (folder / "_mau" / "phong-cach.json").exists()
    if f.exists():
        try:
            m = {k: v for k, v in json.loads(f.read_text(encoding="utf-8")).items() if k in COMP_IDS and v}
        except Exception:
            m = {}
        if has_mau:  # có video mẫu: mục nào không chọn từ bộ đã lưu thì học từ video mẫu
            m = {c: m.get(c, "_mau") for c in COMP_IDS}
        return m
    n = chosen(folder)
    if n and load(n):
        return {c: n for c in COMP_IDS}
    if has_mau:
        return {c: "_mau" for c in COMP_IDS}
    d = default_style()
    if d:
        return {c: d for c in COMP_IDS}
    return {}


def default_mode() -> str:
    """⚙ Cài đặt "Khi dự án không chọn phong cách": '' = Claude tự chọn theo nội dung | '_goc' = kiểu gốc của tool | tên bộ"""
    try:
        return json.loads((ROOT / "settings.json").read_text(encoding="utf-8")).get("defaultStyle") or ""
    except Exception:
        return ""


def default_style() -> str:
    """bộ phong cách mặc định (⚙ Cài đặt) cho dự án không chọn gì; '' = không (Claude tự chọn / kiểu gốc)"""
    try:
        n = json.loads((ROOT / "settings.json").read_text(encoding="utf-8")).get("defaultStyle") or ""
    except Exception:
        return ""
    return n if n and load(n) else ""


def set_mix(folder: Path, mix: dict):
    mix = {k: v for k, v in (mix or {}).items() if k in COMP_IDS and v}
    (folder / "phong-cach-tron.json").write_text(json.dumps(mix, ensure_ascii=False, indent=1), encoding="utf-8")
    (folder / "phong-cach.txt").unlink(missing_ok=True)


# NHÓM CHỦ ĐỀ của thư viện phong cách (để dễ tìm). Bộ có "nhom" trong phong-cach.json thì theo đó, không thì đoán theo tên/mô tả.
GROUPS = [
    ("nhip", "🎵 Dựng theo nhịp nhạc", r"^nhịp ·"),
    ("bds", "🏠 Bất động sản", r"bđs|bất động sản|căn hộ|mở bán|sang trọng|thượng lưu|indochine|đông dương|địa trung hải|hoàng gia|tân cổ điển|japandi|doanh nhân"),
    ("tin", "📰 Tin tức & kiến thức", r"tin |tin$|tin tức|bản tin|infographic|số liệu|kiến thức|hướng dẫn|editorial|dữ liệu|tech|công nghệ|phân tích|bản đồ|vị trí"),
    ("tho", "🌙 Thơ & thủy mặc", r"thơ|thủy mặc|thuỷ mặc"),
    ("chill", "☕ Chill · vlog · lofi", r"vlog|lofi|chill|pastel|cà phê|du lịch|thiên nhiên|nhẹ nhàng|papercut|giấy"),
    ("kechuyen", "🎬 Điện ảnh & kể chuyện", r"điện ảnh|kể chuyện|đen trắng|camcorder|retro|hoài niệm|trailer"),
    ("nangdong", "⚡ Năng động · TikTok", r"năng động|tiktok|thử thách|neon|sự kiện|seecut|motion|bùng nổ"),
    ("podcast", "🎙 Podcast & người nói", r"podcast|talking|người nói"),
]
GROUP_NAMES = {g[0]: g[1] for g in GROUPS} | {"cuatoi": "👤 Của tôi", "khac": "Khác"}


def is_ae(j: dict) -> bool:
    """bộ dùng hiệu ứng kiểu After Effects (lớp phủ, chữ động, chuyển động mượt…) — lọc riêng ✨ Motion kiểu AE"""
    st = j.get("style") or {}
    an = (st.get("text") or {}).get("anim")
    return bool(re.search(r"\bAE\b", j.get("ten") or "") or isinstance((st.get("effects") or {}).get("overlay"), list)
                or st.get("motion") or an in ("stagger", "wave", "flip3d", "maskUp", "rise", "typeCursor", "glitch", "scramble"))
FAV = DIR / "_yeu-thich.json"


def group_of(name: str, j: dict) -> str:
    if j.get("nhom") in GROUP_NAMES:
        return j["nhom"]
    txt = f"{j.get('ten') or name}".lower()
    for gid, _, rx in GROUPS:
        if re.search(rx, txt, re.I):
            return gid
    if (j.get("nguon") or "tạo sẵn") != "tạo sẵn":
        return "cuatoi"
    txt2 = (j.get("mo_ta") or "").lower()
    for gid, _, rx in GROUPS:
        if re.search(rx, txt2, re.I):
            return gid
    return "khac"


def favs() -> list:
    try:
        return [x for x in json.loads(FAV.read_text(encoding="utf-8")) if isinstance(x, str)]
    except Exception:
        return []


def set_fav(name: str, on: bool) -> list:
    L = [x for x in favs() if x != name]
    if on:
        L.insert(0, name)
    FAV.write_text(json.dumps(L, ensure_ascii=False, indent=1), encoding="utf-8")
    return L


def list_styles() -> list:
    out = []
    fv = favs()
    if DIR.is_dir():
        for d in sorted(p for p in DIR.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
            j = load(d.name) or {}
            st = j.get("style") or {}
            out.append({"name": d.name, "ten": j.get("ten") or d.name, "mo_ta": j.get("mo_ta", ""),
                        "font": st.get("font"), "heading": st.get("heading"), "caption": (st.get("captions") or {}).get("preset"),
                        "thumb": (d / "mau.jpg").exists(), "demo": (d / "demo.jpg").exists(),
                        "comps": [c for c in COMP_IDS if has_comp(j, c)], "thanhPhan": descs(j),
                        "nhom": group_of(d.name, j), "fav": d.name in fv, "ae": is_ae(j), "mine": (j.get("nguon") or "tạo sẵn") != "tạo sẵn",
                        "v": int(max([p.stat().st_mtime for p in d.glob("*.jpg")] or [0])),
                        "ghiChu": (d / "ghi-chu.md").read_text(encoding="utf-8") if (d / "ghi-chu.md").exists() else ""})
    return out


def load(name: str):
    f = DIR / slug(name) / "phong-cach.json"
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def chosen(folder: Path) -> str:
    f = folder / "phong-cach.txt"
    return f.read_text(encoding="utf-8").strip() if f.exists() else ""


def project_style(folder: Path):
    """phong cách đã trộn của dự án: mỗi thành phần lấy từ nguồn đã chọn (bộ đã lưu / video mẫu / mặc định)."""
    mix = mix_of(folder)
    if not mix:
        return None
    out = {"style": {}, "plan": {}, "thanhPhan": {}, "nguon": {}, "ghiChu": {}}
    cache = {}
    names = []
    for comp, src in mix.items():
        if src not in cache:
            cache[src] = source(folder, src)
        ps = cache[src]
        if not ps:
            continue
        x = extract(ps, comp)
        out["style"].update(x["style"])
        out["plan"].update(x["plan"])
        if (ps.get("thanhPhan") or {}).get(comp):
            out["thanhPhan"][comp] = ps["thanhPhan"][comp]
        out["nguon"][comp] = src
        if ps.get("ten") and ps["ten"] not in names:
            names.append(ps["ten"])
    out["ten"] = " + ".join(names) if names else ""
    # nhạc: chỉ lấy âm lượng (file nhạc là của từng dự án)
    mv = out["plan"].pop("musicVolume", None)
    if mv is not None:
        out["plan"]["music"] = {"volume": mv}
    return out


def _merge(a: dict, b: dict) -> dict:
    out = dict(a or {})
    for k, v in (b or {}).items():
        out[k] = _merge(out.get(k), v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def apply(folder: Path, plan: dict) -> dict:
    """trộn phong cách vào plan: thông số trong plan.json luôn được ưu tiên."""
    ps = project_style(folder)
    if not ps:
        return plan
    plan["style"] = _merge(ps.get("style") or {}, plan.get("style") or {})
    for k, v in (ps.get("plan") or {}).items():
        if k == "music" and "music" not in plan:
            continue  # chưa có nhạc thì âm lượng nhạc không có tác dụng
        if k not in plan:
            plan[k] = v
        elif isinstance(v, dict) and isinstance(plan[k], dict):
            plan[k] = _merge(v, plan[k])
    return plan


def save_from_project(folder: Path, name: str) -> Path:
    src = folder / "_mau" / "phong-cach.json"
    if not src.exists() and not mau_style(folder):
        raise FileNotFoundError("Chưa có _mau/phong-cach.json (Claude chưa phân tích video mẫu của dự án này)")
    d = DIR / slug(name)
    d.mkdir(parents=True, exist_ok=True)
    j = mau_style(folder) or json.loads(src.read_text(encoding="utf-8"))
    j["ten"] = name
    if not j.get("beatStyle") and not (j.get("style") or {}).get("beat"):  # mẫu có nhạc nền -> học luôn KIỂU DỰNG NHỊP
        try:
            pt = json.loads((folder / "_mau" / "_phan-tich" / "phan-tich.json").read_text(encoding="utf-8"))
            mu = pt.get("nhac") or {}
            if mu.get("bpm") or mu.get("coNhacNen"):
                import dung_nhip  # noqa
                j.setdefault("style", {})["beat"] = dung_nhip.hoc(pt)
        except Exception:  # noqa
            pass
    (d / "phong-cach.json").write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
    if (folder / "_mau" / "ghi-chu.md").exists():
        shutil.copyfile(folder / "_mau" / "ghi-chu.md", d / "ghi-chu.md")
    pa = folder / "_mau" / "_phan-tich"
    try:  # 1 khung nét (ô đầu của chu_01.jpg); không có thì 1 ô của lưới từng giây
        from PIL import Image
        if (pa / "chu_01.jpg").exists():
            im = Image.open(pa / "chu_01.jpg")
            im.crop((0, 30, min(540, im.width), im.height)).convert("RGB").save(d / "mau.jpg", quality=88)
        elif (pa / "khung_01.jpg").exists():
            shutil.copyfile(pa / "khung_01.jpg", d / "mau.jpg")
    except Exception as e:  # noqa
        print("[!] Không tạo được ảnh mẫu:", e)
    return d


def save_from_result(folder: Path, name: str) -> Path:
    """LƯU PHONG CÁCH TỪ VIDEO ĐÃ DỰNG (plan.json + phong cách đang áp) -> bộ dùng lại cho dự án khác.
    Lấy kiểu chữ / phụ đề / chuyển cảnh / hiệu ứng / màu / âm thanh / bố cục đúng như bản đã ưng (gồm cả chỉnh tay)."""
    from collections import Counter
    pj = folder / "plan.json"
    if not pj.exists():
        raise FileNotFoundError("Dự án chưa có plan.json (chưa dựng)")
    raw = json.loads(pj.read_text(encoding="utf-8"))
    plan = apply(folder, json.loads(json.dumps(raw)))
    st = json.loads(json.dumps(plan.get("style") or {}))
    els = [e for e in plan.get("elements") or [] if isinstance(e, dict)]
    dur = float(plan.get("durationSec") or 0) or max([e.get("end", 0) for e in els] + [1])
    if plan.get("segments"):
        dur = sum(b - a for a, b in plan["segments"])

    def common(items, key):
        c = Counter(x.get(key) for x in items if x.get(key) not in (None, ""))
        return c.most_common(1)[0][0] if c else None

    texts = [e for e in els if e.get("type") == "text"]
    if texts:  # kiểu chữ dùng nhiều nhất trong video
        t = dict(st.get("text") or {})
        for k in ("look", "font", "weight", "size", "color", "bg", "hlColor", "hlStyle", "stroke", "strokeColor", "shadow", "anim", "out", "upper", "italic", "radius", "spacing"):
            v = common(texts, k)
            if v is not None:
                t[k] = v
        st["text"] = t
    zooms = [e for e in els if e.get("type") == "zoom"]
    ef = dict(st.get("effects") or {})
    per_min = len(zooms) / max(dur / 60, 0.1)
    ef["zoom"] = "không" if not zooms else "nhiều" if per_min >= 8 else "vừa" if per_min >= 4 else "ít"
    if zooms:
        ef["zoomStyle"] = common(zooms, "style") or "punch"
    if plan.get("shots"):
        ef["shots"] = "auto"
    st["effects"] = ef
    brolls = [e for e in els if e.get("type") == "broll"]
    if brolls:
        b = dict(st.get("broll") or {})
        for k, kk in (("transition", "enter"), ("exit", "exit"), ("area", "area"), ("split", "split"), ("feather", "feather"), ("seam", "seam")):
            v = common(brolls, k)
            if v is not None:
                b[kk] = v
        st["broll"] = b
    pips = [e for e in els if e.get("type") == "pip"]
    if pips and common(pips, "look"):
        st.setdefault("broll", {})["pip"] = common(pips, "look")
    sfxn = sum(1 for e in els if e.get("sfx")) + (1 if plan.get("joinSfx") else 0)
    sp = sfxn / max(dur / 60, 0.1)
    st["sfx"] = {**(st.get("sfx") or {}), "density": "it" if sp < 6 else "vua" if sp < 14 else "nhieu", "joins": bool(plan.get("joinSfx"))}
    if not any(e.get("type") in ("priceHook", "chip", "checklist", "rangeCard", "bigQuestion", "cta") for e in els) and texts:
        st.setdefault("templates", False)
    pkeys = ("captionTop", "captionX", "wordsPerPage", "captionSize", "captionUpper", "transition", "cutFx", "color", "sfxVolume",
             "theme", "shotFade", "capZ")
    pl = {k: plan[k] for k in pkeys if k in plan}
    if isinstance(plan.get("music"), dict) and plan["music"].get("volume") is not None:
        pl["musicVolume"] = plan["music"]["volume"]
    # mô tả ngắn từng thành phần (hiện trên giao diện để tích chọn)
    tx = st.get("text") or {}
    cap = st.get("captions") or {}
    kinds = Counter(e.get("type") for e in els if e.get("type") not in ("zoom", "audio", "sfx", "dayBadge"))
    tp = {
        "chu": f"{tx.get('font') or st.get('font') or 'font mặc định'}, kiểu {tx.get('look') or 'plain'}, hiện {tx.get('anim') or 'pop'}" if tx else "",
        "phude": (f"kiểu {cap.get('preset')}" if cap.get("preset") else "phụ đề mặc định") + (", tắt" if plan.get("captions") in (False, None) else ""),
        "chuyencanh": f"nối đoạn: {plan.get('transition') or 'tự động'}",
        "hieuung": ("tự đổi cỡ cảnh toàn–trung–cận" if plan.get("shots") else f"zoom {ef['zoom']}" + (f" ({ef.get('zoomStyle')})" if zooms else "")),
        "dohoa": ", ".join(f"{k} ×{n}" for k, n in kinds.most_common(3)) or "ít đồ họa",
        "minhhoa": (f"{len(brolls)} cảnh trám" + (f" nửa {'trên' if (st.get('broll') or {}).get('area') == 'top' else 'dưới'}" if (st.get("broll") or {}).get("area") in ("top", "bottom") else "")) if brolls else "ít cảnh trám",
        "amthanh": f"sfx {st['sfx']['density']}" + (", có nhạc nền" if plan.get("music") else ""),
        "mau": "chỉnh màu riêng" if plan.get("color") else "giữ màu gốc",
    }
    tp = {k: v[:60] for k, v in tp.items() if v}
    j = {"ten": name, "mo_ta": f"Lưu từ video đã dựng \"{folder.name}\"", "nguon": f"video {folder.name}", "style": st, "plan": pl, "thanhPhan": tp}
    d = DIR / slug(name)
    d.mkdir(parents=True, exist_ok=True)
    (d / "phong-cach.json").write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
    # ghi chú cách dựng cho Claude (mật độ, vị trí, loại khối)
    gap = dur / max(1, len([e for e in els if e.get("type") not in ("zoom", "audio", "sfx", "dayBadge")]))
    ys = [e.get("y") for e in els if isinstance(e.get("y"), (int, float))]
    notes = [f"# Ghi chú cách dựng — lưu từ video \"{folder.name}\" ({dur:.0f}s)",
             f"- Mật độ: khoảng {gap:.1f}s một chữ/đồ họa; loại dùng nhiều: " + (", ".join(f"{k} ({n})" for k, n in kinds.most_common(6)) or "ít"),
             f"- Vị trí dọc thường dùng: {int(sorted(ys)[len(ys) // 2])}px (trung vị)" if ys else "- Vị trí: theo mặc định",
             f"- Zoom: {len(zooms)} lần ({per_min:.1f}/phút)" + (f", kiểu {ef.get('zoomStyle')}" if zooms else "") + ("; tự đổi cỡ cảnh" if plan.get("shots") else ""),
             f"- Cảnh trám: {len(brolls)} lần" + (f", vùng {(st.get('broll') or {}).get('area')}" if (st.get("broll") or {}).get("area") else ""),
             f"- Âm thanh: {sfxn} tiếng hiệu ứng ({sp:.1f}/phút)" + (", có nhạc nền" if plan.get("music") else ""),
             "- Mở đầu (3s đầu): " + (", ".join(sorted({e.get("type") for e in els if e.get("start", 99) < 3 and e.get("type") != "dayBadge"})) or "không có chữ")]
    tx0 = [e.get("text", "").replace("\n", " ")[:40] for e in texts[:6]]
    if tx0:
        notes.append("- Ví dụ chữ đã dùng: " + " | ".join(tx0))
    (d / "ghi-chu.md").write_text("\n".join(n for n in notes if n) + "\n", encoding="utf-8")
    # ảnh mẫu: 1 khung của final.mp4 lúc có chữ
    fin = folder / "final.mp4"
    if fin.exists():
        import subprocess
        tt = next((e.get("start", 0) + 0.6 for e in texts), min(3.0, dur / 2))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{tt:.2f}", "-i", str(fin), "-frames:v", "1", "-vf", "scale=540:-2", str(d / "mau.jpg")])
    return d


def render_preview(name: str) -> Path:
    """vẽ ảnh minh họa phong cách bằng bộ dựng (Remotion) -> phong-cach/<tên>/demo.jpg"""
    import hashlib
    import os
    import subprocess
    d = DIR / slug(name)
    j = load(name)
    if not j:
        raise FileNotFoundError("Không có phong cách " + name)
    pub = ROOT / "public" / "jobs"
    pub.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(d.name.encode()).hexdigest()[:8]
    props = {"style": j.get("style") or {}, "theme": None, "blocks": (j.get("style") or {}).get("templates") is not False}
    brand = ROOT / "brand.json"
    if (j.get("plan") or {}).get("theme"):
        props["theme"] = j["plan"]["theme"]
    elif brand.exists():
        props["theme"] = json.loads(brand.read_text(encoding="utf-8")).get("theme")
    if (d / "mau.jpg").exists():
        shutil.copyfile(d / "mau.jpg", pub / f"_style_{key}.jpg")
        props["bg"] = f"jobs/_style_{key}.jpg"
    comp = "stylepreview"
    beat = ((j.get("style") or {}).get("beat") or {}).get("preset")
    if beat:  # bộ dựng theo nhịp nhạc: ảnh thể hiện kiểu dựng (chia khung, dải chéo, viền phim, glitch…) + timeline nhịp
        comp = "beatpreview"
        props["preset"] = beat
        ims = []
        for k, f in enumerate(sorted(d.glob("demo-anh*.jpg")) or ([d / "mau.jpg"] if (d / "mau.jpg").exists() else [])):
            shutil.copyfile(f, pub / f"_style_{key}_{k}.jpg")
            ims.append(f"jobs/_style_{key}_{k}.jpg")
        props["imgs"] = ims
        props.pop("bg", None)
    pf = pub / f"_style_{key}.json"
    pf.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    png = pub / f"_style_{key}.png"
    npx = "npx.cmd" if os.name == "nt" else "npx"
    entry = "remotion/src/index.ts"
    if not (ROOT / "remotion" / "src").exists():  # bản phát hành: dùng bộ dựng đóng gói sẵn
        import render as _r
        entry = str(_r.bundle_dir() or entry)
    cmd = [npx, "remotion", "still", entry, comp, str(png), "--frame=40", f"--props={pf}", "--log=error"]
    if os.environ.get("REMOTION_BROWSER"):
        cmd.append(f"--browser-executable={os.environ['REMOTION_BROWSER']}")
    r = subprocess.run(cmd, cwd=ROOT)
    try:
        if r.returncode or not png.exists():
            raise RuntimeError("Không vẽ được ảnh minh họa")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(png), "-vf", "scale=540:-2", "-q:v", "3", str(d / "demo.jpg")])
    finally:
        for p in pub.glob(f"_style_{key}*"):
            p.unlink(missing_ok=True)
    return d / "demo.jpg"


def kieu_chu_note(f: Path):
    """in KIỂU CHỮ người dùng chọn thêm cho dự án (kieu-chu.json) kèm thông số — Claude dùng đúng các kiểu này khi viết plan"""
    try:
        ids = json.loads((f / "kieu-chu.json").read_text(encoding="utf-8")).get("ids", [])
    except Exception:
        return
    if not ids:
        return
    try:
        lib = json.loads((ROOT / "gui" / "editor" / "presets.json").read_text(encoding="utf-8"))
    except Exception:
        lib = {}
    cats = dict(lib.get("textCats") or [])
    by = {x["id"]: x for x in lib.get("text") or []}
    print("KIỂU CHỮ NGƯỜI DÙNG CHỌN THÊM (kieu-chu.json) — dùng ĐÚNG các kiểu này cho khối chữ, tự cân đối theo vai trò "
          "(hook/tiêu đề, giá & số, từ khoá, trích dẫn, kêu gọi…): mỗi chữ chọn kiểu hợp vai trò nhất; chép thông số (look, font, màu, "
          "anim, out, ease, mblur…), chỉ đổi text / y / thời gian; phong cách vẫn quyết định phụ đề, chuyển cảnh, màu… "
          "Đừng dùng 1 kiểu cho mọi chữ, đừng trộn quá 3–4 kiểu trong 1 video:")
    for i in ids:
        x = by.get(i)
        if not x:
            continue
        e = {k: v for k, v in x["els"][0].items() if k not in ("at", "dur", "type", "text", "y")}
        print(f"  - [{cats.get(x.get('cat'), x.get('cat'))}] {x['name']}: {json.dumps(e, ensure_ascii=False)}")
    print()


# ---------- gửi / nhận phong cách (file .phongcach = zip của thư mục phong-cach/<tên>) ----------
GOI_EXT = {".json", ".md", ".jpg", ".jpeg", ".png", ".txt", ".webp"}
# khối đặc biệt cần bản tool đủ mới: tên khối -> file mã nguồn phải có
NEED_FILES = {"orbit": "remotion/src/Orbit.tsx", "mapTour": "remotion/src/MapTour.tsx", "map": "remotion/src/MapBlock.tsx"}


def _needs(j: dict, note: str) -> list:
    t = json.dumps(j, ensure_ascii=False) + "\n" + note
    out = [k for k in NEED_FILES if re.search(r'["`\s(]' + re.escape(k) + r'["`\s)]', t) or (k in (j.get("style") or {}))]
    if "mapTour" in out and "map" in out and '"map"' not in json.dumps(j.get("style") or {}):
        out.remove("map")
    return out


def pack(name: str) -> tuple:
    """-> (tên file, bytes) của gói .phongcach để gửi cho người khác"""
    import io, zipfile, time
    d = DIR / slug(name)
    j = load(name)
    if not j or not d.is_dir():
        raise FileNotFoundError(name)
    note = (d / "ghi-chu.md").read_text(encoding="utf-8") if (d / "ghi-chu.md").exists() else ""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(d.iterdir()):
            # mau.jpg = khung cắt từ video mẫu của người khác -> không gửi đi (chỉ gửi ảnh tool tự dựng)
            if f.is_file() and f.suffix.lower() in GOI_EXT and f.name != "mau.jpg" and f.stat().st_size < 15_000_000:
                z.write(f, f.name)
        z.writestr("_goi.json", json.dumps({"ten": j.get("ten") or d.name, "thuMuc": d.name, "can": _needs(j, note),
                                            "ngay": time.strftime("%Y-%m-%d")}, ensure_ascii=False, indent=1))
    return f"{d.name}.phongcach", buf.getvalue()


def unpack(data: bytes) -> dict:
    """nhận gói .phongcach -> thêm vào thư viện (trùng tên thì thêm (2), (3)…; không đè bộ đang có)"""
    import io, zipfile
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("File không phải gói phong cách (.phongcach)")
    names = [i for i in z.infolist() if not i.is_dir()]
    if sum(i.file_size for i in names) > 60_000_000:
        raise ValueError("Gói quá lớn")
    # chấp nhận cả zip có 1 thư mục bọc ngoài
    pj = next((i for i in names if i.filename.rsplit("/", 1)[-1] == "phong-cach.json"), None)
    if not pj:
        raise ValueError("Gói thiếu phong-cach.json")
    pre = pj.filename[: -len("phong-cach.json")]
    j = json.loads(z.read(pj).decode("utf-8"))
    meta = {}
    if (pre + "_goi.json") in z.namelist():
        try:
            meta = json.loads(z.read(pre + "_goi.json").decode("utf-8"))
        except Exception:
            meta = {}
    base = slug(j.get("ten") or meta.get("ten") or "Phong cách nhận")
    nm, k = base, 2
    while (DIR / nm).exists():
        nm = f"{base} ({k})"
        k += 1
    dest = DIR / nm
    dest.mkdir(parents=True)
    for i in names:
        if not i.filename.startswith(pre):
            continue
        fn = i.filename[len(pre):]
        if "/" in fn or "\\" in fn or fn.startswith(".") or fn == "_goi.json" or Path(fn).suffix.lower() not in GOI_EXT:
            continue  # chỉ nhận file dữ liệu phẳng (json / md / ảnh) — không nhận mã chạy được
        (dest / fn).write_bytes(z.read(i))
    if nm != base:
        j["ten"] = f"{j.get('ten') or base} ({nm[len(base):].strip(' ()')})"
    j.pop("nhom", None) if j.get("nhom") == "cuatoi" else None
    (dest / "phong-cach.json").write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
    can = meta.get("can") or _needs(j, (dest / "ghi-chu.md").read_text(encoding="utf-8") if (dest / "ghi-chu.md").exists() else "")
    thieu = [k for k in can if k in NEED_FILES and not (ROOT / NEED_FILES[k]).exists()]
    return {"name": nm, "ten": j.get("ten") or nm, "thieu": thieu, "demo": (dest / "demo.jpg").exists()}


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["ds"]:
        L = list_styles()
        fv = [s for s in L if s["fav"]]
        print("(✨ = có hiệu ứng kiểu AE: lớp phủ / chữ động / chuyển động mượt)")
        if fv:
            print("⭐ YÊU THÍCH của người dùng (ưu tiên chọn khi hợp nội dung):")
            for s in fv:
                print(f"- {s['name']}: {s['mo_ta']}  (font {s['font'] or 'mặc định'})")
        for gid, gname in list(GROUP_NAMES.items()):
            xs = [s for s in L if s["nhom"] == gid and not s["fav"]]
            if xs:
                print(f"\n{gname}:")
                for s in xs:
                    print(f"- {'✨ ' if s['ae'] else ''}{s['name']}: {s['mo_ta']}  (font {s['font'] or 'mặc định'})")
        if not list_styles():
            print("(chưa có bộ phong cách nào)")
    elif a[:1] == ["xuat"] and len(a) > 1:  # gói .phongcach để gửi người khác
        fn, b = pack(a[1])
        out = Path(a[2]) if len(a) > 2 else ROOT / fn
        out.write_bytes(b)
        print("Đã tạo gói:", out)
    elif a[:1] == ["nhap"] and len(a) > 1:
        r = unpack(Path(a[1]).read_bytes())
        print("Đã thêm phong cách:", r["ten"], "->", DIR / r["name"])
        if r["thieu"]:
            print("[!] Bộ này dùng khối mà bản tool này chưa có:", ", ".join(r["thieu"]), "— cần cập nhật tool.")
    elif a[:1] == ["xem"] and len(a) > 1:
        print(json.dumps(load(a[1]), ensure_ascii=False, indent=1))
        g = DIR / slug(a[1]) / "ghi-chu.md"
        print(g.read_text(encoding="utf-8") if g.exists() else "(không có ghi-chu.md)")
    elif a[:1] == ["chon"] and len(a) > 2:
        set_mix(Path(a[1]).resolve(), {c: a[2] for c in COMP_IDS} if a[2] else {})
        print("Đã chọn:", a[2] or "(không)")
    elif a[:1] == ["luu-ketqua"] and len(a) > 2:  # lưu phong cách từ video ĐÃ DỰNG (plan.json) — không đổi phong cách của dự án
        d = save_from_result(Path(a[1]).resolve(), a[2])
        print("Đã lưu:", d)
        print("Ảnh minh họa:", render_preview(d.name))
    elif a[:1] == ["luu"] and len(a) > 2:
        d = save_from_project(Path(a[1]).resolve(), a[2])
        f = Path(a[1]).resolve()
        mix = mix_of(f)
        set_mix(f, {c: (d.name if v == "_mau" else v) for c, v in mix.items()} or {c: d.name for c in COMP_IDS})
        print("Đã lưu:", d)
        print("Ảnh minh họa:", render_preview(d.name))
    elif a[:1] == ["tron"] and len(a) > 1:
        f = Path(a[1]).resolve()
        kieu_chu_note(f)
        try:  # logo + SĐT người dùng tự chèn khi xuất -> đừng đặt chữ đè chỗ đó
            import thuong_hieu
            n = thuong_hieu.note(f)
            if n:
                print(n)
        except Exception:
            pass
        mix = mix_of(f)
        if not mix:
            if default_mode() == "_goc":
                print("Dự án KHÔNG chọn phong cách — người dùng đặt dùng KIỂU GỐC của tool (không tự chọn bộ).")
            else:
                print("Dự án CHƯA CHỌN PHONG CÁCH -> Claude TỰ CHỌN: đọc lời thoại + brief, xem `python scripts/phongcach.py ds`,"
                      " chọn 1 bộ hợp nội dung nhất (theo bảng chủ đề → bộ trong CLAUDE.md) rồi chạy"
                      f' `python scripts/phongcach.py chon "{f}" "<tên bộ>"`, ghi lý do vào bao-cao.md, rồi chạy lại lệnh này.')
            sys.exit(0)
        labels = {c[0]: c[1] for c in COMPONENTS}
        ps = project_style(f) or {}
        for c in COMP_IDS:
            src = mix.get(c, "")
            print(f"- {labels[c]}: {('video mẫu của dự án' if src == '_mau' else src) or 'mặc định của tool'}"
                  + (f" — {ps.get('thanhPhan', {}).get(c)}" if ps.get("thanhPhan", {}).get(c) else ""))
        print(json.dumps({"style": ps.get("style"), "plan": ps.get("plan")}, ensure_ascii=False, indent=1))
        for src in sorted(set(mix.values())):  # ghi chú cách dựng của từng nguồn
            g = (f / "_mau" / "ghi-chu.md") if src == "_mau" else DIR / slug(src) / "ghi-chu.md"
            if g.exists():
                print(f"\n## Ghi chú cách dựng — {src} (chỉ áp phần thuộc thành phần đã chọn từ nguồn này)\n" + g.read_text(encoding="utf-8"))
    elif a[:1] == ["anh"] and len(a) > 1:
        print("Ảnh minh họa:", render_preview(a[1]))
    else:
        sys.exit(__doc__)
