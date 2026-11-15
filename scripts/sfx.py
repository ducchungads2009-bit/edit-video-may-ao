"""HIỆU ỨNG ÂM THANH: thư viện + tự gán cho từng chữ / đồ họa / chuyển cảnh.

Thư viện: public/sfx/*.wav (danh sách + loại + khi nào dùng: public/sfx/sfx.json) và âm thanh riêng của bạn trong
public/sfx/cua-ban/ (tên gọi "cua-ban/<tên file>").

Dùng:
  python scripts/sfx.py ds                                  liệt kê thư viện theo loại
  python scripts/sfx.py tu-gan "<folder>" [--it|--nhieu] [--ghi-de] [--khong-chuyen-canh]
        tự chọn âm thanh hợp với từng element trong plan.json (mặc định chỉ điền chỗ chưa có, mật độ vừa)
"""
import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
SFX = ROOT / "public" / "sfx"
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}
CATS = {"chuyen-canh": "Chuyển cảnh", "nhan-manh": "Nhấn mạnh", "hien-chu": "Hiện chữ / giao diện", "vui": "Vui nhộn",
        "thong-bao": "Thông báo / tiền", "hieu-ung": "Hiệu ứng khác", "cua-ban": "Của bạn"}
GUESS = [("chuyen-canh", r"whoosh|swoosh|swish|swipe|transition|riser|wind|vut"),
         ("nhan-manh", r"boom|impact|hit|punch|bass|drop|dap"),
         ("hien-chu", r"pop|click|tick|type|typing|key|bubble"),
         ("thong-bao", r"ding|bell|cash|coin|money|notif|success|chime"),
         ("vui", r"boing|cartoon|funny|laugh|tada|spring")]


def library() -> list:
    lib = []
    try:
        lib = json.loads((SFX / "sfx.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    have = {x["name"] for x in lib}
    for p in sorted(SFX.glob("*.wav")):  # file thêm tay chưa có trong sfx.json
        if p.stem not in have:
            lib.append({"name": p.stem, "cat": "hieu-ung", "desc": p.stem, "use": ""})
    mine = SFX / "cua-ban"
    if mine.is_dir():
        for p in sorted(mine.iterdir()):
            if p.suffix.lower() in AUDIO_EXT:
                g = next((c for c, rx in GUESS if re.search(rx, p.stem, re.I)), "cua-ban")
                lib.append({"name": f"cua-ban/{p.name}", "cat": "cua-ban", "guess": g, "desc": p.stem, "use": "âm thanh của bạn"})
    return lib


# độ ưu tiên: 3 = khoảnh khắc chính (luôn có), 2 = nên có, 1 = phụ
def choose(e: dict, style: dict) -> tuple:
    """-> (tên âm thanh hoặc None, độ ưu tiên)"""
    ty = e.get("type")
    txt = " ".join(str(e.get(k, "")) for k in ("text", "price", "label", "value", "title", "icon")).lower()
    st_text = (style.get("text") or {})
    anim = e.get("anim") or st_text.get("anim") or "pop"
    big = (e.get("size") or st_text.get("size") or 80) >= 120
    hook = e.get("start", 9) < 3

    def by_words(default):
        if re.search(r"\d+([,.]\d+)?\s*(tỷ|tỉ|triệu|tr\b|k\b|nghìn|đ|vnd|\$)|giá|chiết khấu|ưu đãi|lãi", txt):
            return "cash"
        if re.search(r"follow|theo dõi|inbox|nhắn tin|liên hệ|đăng ký|subscribe", txt):
            return "bell"
        if re.search(r"sai lầm|đừng|không nên|cẩn thận|lỗi|❌|\bx\b", txt):
            return "error"
        if re.search(r"thành công|chốt|đạt|xong|✅|check", txt):
            return "success"
        return default

    if ty == "text":
        base = {"type": "typing", "words": "click", "pop": "pop", "bounce": "pop", "up": "swoosh", "down": "swoosh",
                "left": "swoosh", "right": "swoosh", "blur": "whoosh-nhe", "fade": "whoosh-nhe", "wipe": "swipe",
                "zoomOut": "whoosh", "none": None, "stagger": "pop", "wave": "swoosh", "flip3d": "swoosh",
                "maskUp": "swoosh", "rise": "whoosh-nhe", "typeCursor": "typing", "glitch": "glitch", "scramble": "typing"}.get(anim, "pop")
        if big and anim in ("pop", "bounce", "zoomOut"):
            base = "boom" if hook else "hit"
        look = e.get("look") or st_text.get("look")
        if look in ("neon", "gold") and base in ("pop", "whoosh-nhe"):
            base = "sparkle"
        name = by_words(base)
        return name, 3 if (hook or big or name in ("cash", "bell")) else 1
    if ty == "sticker":
        ic = str(e.get("icon", ""))
        name = by_words("bubble" if not re.match(r"^[A-Za-z]", ic) else "pop")
        if e.get("loop") == "bounce" or (e.get("anim") == "bounce"):
            name = "boing" if name == "bubble" else name
        return name, 2
    if ty == "chip":
        return "tick", 1
    if ty == "priceHook":
        return "cash", 3
    if ty == "rangeCard":
        return by_words("hit"), 2
    if ty == "bigQuestion":
        return "impact", 3
    if ty == "checklist":
        return "pop", 2
    if ty == "cta":
        return "bell", 3
    if ty == "broll":
        half = (e.get("area") or (style.get("broll") or {}).get("area") or "full") != "full"
        tr = e.get("transition") or (style.get("broll") or {}).get("enter") or ("fade" if half else "zoom")
        return {"whip": "whoosh-manh", "slide": "swoosh", "up": "swoosh", "circle": "whoosh-nhe", "fade": "whoosh-nhe",
                "cut": None, "zoom": "whoosh"}.get(tr, "whoosh"), 2
    if ty == "pip":
        src = str(e.get("src", "")).lower()
        return ("camera" if re.search(r"\.(jpe?g|png|webp)$", src) else "pop"), 2
    if ty == "phrase":
        return by_words("pop"), 2
    if ty == "counter":
        return by_words("cash" if re.search(r"tỷ|triệu|đồng|vnđ|\$", str(e.get("suffix", "")) + str(e.get("label", "")), re.I) else "riser"), 3
    if ty == "stamp":
        return ("success" if e.get("icon") in ("check", "v") else "impact"), 3
    if ty in ("tabs", "tiles"):
        return "tick", 1
    if ty == "note":
        return "pop", 2
    if ty == "bubble":
        return "bubble", 2
    if ty == "chart":
        return "pop", 2
    if ty == "spark":
        return "sparkle", 1
    if ty == "shape":
        k = e.get("kind") or "arrow"
        return {"check": "success", "cross": "error", "callout": "pop", "arrow": "swoosh", "line": "swipe", "circle": "swipe",
                "underline": "swipe", "box": "swipe", "bracket": "click"}.get(k, "swipe"), 1
    if ty == "text3d":
        return by_words("boom" if hook else "whoosh"), 3
    if ty == "card3d":
        return ("whoosh" if (e.get("move") or "orbit") in ("flyIn", "flip") else "whoosh-nhe"), 2
    if ty == "scene":
        return {"intro": "riser", "outro": "bell", "pricetable": "cash", "stats": "riser", "compare": "whoosh", "amenities": "pop"}.get(e.get("kind") or "intro", "pop"), 3
    if ty == "overlay":
        k = e.get("kind") or "lightleak"
        return {"filmburn": "whoosh-nhe", "confetti": "tada", "sparkle": "sparkle", "flare": "whoosh-nhe"}.get(k), 1
    if ty == "presenter":
        return ("whoosh-nhe" if (e.get("mode") or "card") != "full" else None), 1
    if ty == "zoom":
        stl = e.get("style") or "punch"
        if (style.get("effects") or {}).get("zoomEase") == "smooth" or stl == "smooth":
            return None, 0
        if stl == "shake":
            return "impact", 3
        if stl == "punch":
            return ("impact" if (e.get("scale") or 1.2) >= 1.25 else "hit"), 2
        return None, 0
    return None, 0


SOFT = {"whoosh-manh": "whoosh-nhe", "impact": "hit", "boom": "hit", "error": "click", "glitch": "swipe"}
LOUD = {"impact": 0.3, "boom": 0.3, "typing": 0.22, "riser": 0.25, "whoosh-manh": 0.28, "glitch": 0.25, "error": 0.25}


# NGÂN SÁCH tiếng hiệu ứng (người dùng thấy dày quá): khoảng cách tối thiểu giữa 2 tiếng, số tiếng tối đa theo độ dài,
# tiếng "gây chú ý" (chuông, ka-ching, đập…) hiếm hơn nữa; chuông chỉ 1 lần (kêu gọi cuối).
BUDGET = {"it": (2.2, 9.0), "vua": (1.5, 5.0), "nhieu": (0.8, 2.8)}  # (giây cách nhau tối thiểu, giây / 1 tiếng)
ATTN = {"bell", "cash", "tada", "boom", "impact", "success", "riser", "notify", "error", "glitch"}


def _joins(plan: dict):
    segs = [x for x in plan.get("segments") or [] if x[1] - x[0] > 0.05]
    out, acc = [], 0.0
    for i, (a, b) in enumerate(segs[:-1]):
        acc += b - a
        out.append((max(0.0, acc - 4 / 30), f"{round(b, 2)}>{round(segs[i + 1][0], 2)}"))
    return out


def _out_dur(plan: dict, dur: float = None):
    segs = [x for x in plan.get("segments") or [] if x[1] - x[0] > 0.05]
    if segs:
        return sum(b - a for a, b in segs)
    ends = [e.get("end", 0) for e in plan.get("elements") or [] if e]
    return dur or (max(ends) if ends else 60)


def events(plan: dict, style: dict = None):
    """mọi tiếng hiệu ứng sẽ phát: (giây, độ ưu tiên, loại, chỉ số, tên). Ưu tiên: 3 khoảnh khắc chính / tiếng đặt riêng,
    2 nên có, 1 phụ; điểm nối = 0,5 (trừ khi người dùng tự chọn tiếng cho điểm nối đó)."""
    style = style or plan.get("style") or {}
    ev = []
    for i, e in enumerate(plan.get("elements") or []):
        if not e or e.get("hidden") or e.get("end", 0) <= e.get("start", 0):
            continue
        if e.get("sfx"):
            pr = 3 if e.get("type") == "sfx" else max(1, choose(e, style)[1] or 1)
            if e.get("type") == "cta":
                pr = 3
            ev.append((max(0.0, e["start"] + (e.get("sfxOff") or 0)), pr, "el", i, e["sfx"]))
        if e.get("type") == "checklist":
            for j, it in enumerate(e.get("items") or []):
                ev.append((max(e["start"], it.get("at", e["start"])), 2, "item", (i, j), "ding"))
    js = plan.get("joinSfx")
    mp = plan.get("joinSfxMap") or {}
    for t, key in _joins(plan):
        ov = mp.get(key)
        if ov:
            ev.append((t, 2, "join", key, ov))
        elif js and ov is None:
            ev.append((t, 0.5, "join", key, js if isinstance(js, str) else "whoosh-nhe"))  # thấp nhất: nhường tiếng của chữ/hình
    return sorted(ev)


def thin(plan: dict, density: str = "vua", style: dict = None, dur: float = None) -> tuple:
    """bỏ bớt tiếng cho đúng ngân sách (giữ tiếng quan trọng, giãn cách đều). Trả (plan, số tiếng bỏ)."""
    gap, per = BUDGET.get(density, BUDGET["vua"])
    total = _out_dur(plan, dur)
    cap = max(3, int(total / per + 0.5))
    cap_attn = max(1, int(total / (per * 3) + 0.5))
    ev = events(plan, style)
    # chỉ 1 "khoảnh khắc chính" ở mỗi cụm chữ hiện liền nhau (vd 3 dòng tiêu đề mở đầu): cái đầu giữ ưu tiên 3
    ev2, last3 = [], -9.0
    for x in ev:
        if x[1] == 3 and x[2] == "el" and x[0] - last3 < 1.2:
            x = (x[0], 2) + x[2:]
        elif x[1] == 3:
            last3 = x[0]
        ev2.append(x)
    ev = ev2
    keep = [x for x in ev if x[2] == "item"]  # dòng checklist: luôn giữ (đã gắn với chữ hiện)
    cand = [x for x in ev if x[2] != "item"]
    last_bell = max((x[0] for x in cand if x[4] == "bell"), default=None)
    state = {"attn": 0, "bell": 0}

    def can(x):
        t, pr, kind, idx, nm = x
        if len([k for k in keep if k[2] != "item"]) >= cap:
            return False
        if any(abs(t - k[0]) < (0.8 if pr == 3 and k[1] == 3 else gap) for k in keep):
            return False
        if nm == "bell" and (state["bell"] >= 1 or t != last_bell):  # chuông: chỉ lần cuối (kêu gọi follow)
            return False
        if nm in ATTN and nm != "bell" and state["attn"] >= cap_attn and pr < 3:
            return False
        return True

    # theo từng mức ưu tiên: lấy dần tiếng CÁCH XA các tiếng đã giữ nhất -> rải đều cả video, không dồn ở đầu
    for lv in (3, 2, 1, 0.5):
        pool = [x for x in cand if x[1] == lv]
        while pool:
            ok = [x for x in pool if can(x)]
            if not ok:
                break
            x = max(ok, key=lambda x: (min([abs(x[0] - k[0]) for k in keep] or [999]), -x[0]))
            keep.append(x)
            pool.remove(x)
            if x[4] in ATTN:
                state["attn"] += 1
                state["bell"] += x[4] == "bell"
    drop = [x for x in cand if x not in keep]
    els = plan.get("elements") or []
    mp = dict(plan.get("joinSfxMap") or {})
    for t, pr, kind, idx, nm in drop:
        if kind == "el":
            els[idx].pop("sfx", None)
            els[idx].pop("sfxVolume", None)
            els[idx].pop("sfxOff", None)
        elif kind == "join":
            mp[idx] = ""
    if mp:
        plan["joinSfxMap"] = mp
    return plan, len(drop)


def auto(plan: dict, density: str = "vua", overwrite: bool = False, joins: bool = True, style: dict = None) -> dict:
    """gán sfx cho các element; trả plan mới. density: it | vua | nhieu"""
    style = style if style is not None else (plan.get("style") or {})
    cfg = style.get("sfx") or {}
    density = cfg.get("density", density) if density == "vua" and cfg.get("density") else density
    soft = cfg.get("set") == "mem"
    names = {x["name"] for x in library()}
    els = plan.get("elements", [])
    if overwrite:  # làm lại từ đầu (giữ âm thanh lấy từ file riêng trong assets/)
        for e in els:
            if e and e.get("sfx") and not str(e["sfx"]).startswith("assets/"):
                e.pop("sfx", None)
                e.pop("sfxVolume", None)
        overwrite = False
    picks = []
    be = plan.get("beatEdit") or {}
    def in_beat(e):  # đoạn dựng theo nhịp nhạc: không gắn tiếng hiệu ứng (nhạc đã đủ nhịp)
        return bool(be.get("on")) and not be.get("keepSfx") and be.get("from", 0) - 0.05 <= e.get("start", -1) <= be.get("to", 1e9)
    for i, e in enumerate(els):
        if not e or (e.get("sfx") and not overwrite) or in_beat(e):
            continue
        n, pr = choose(e, style)
        mp = cfg.get("map") or {}  # học từ video mẫu: loại tiếng hay dùng ở chuyển cảnh / chữ hiện / zoom
        if n and mp:
            ty = e.get("type")
            if ty in ("text", "chip", "sticker", "checklist") and mp.get("text") and n not in ("cash", "bell", "error", "success", "typing"):
                n = mp["text"]
            elif ty in ("broll", "pip") and mp.get("cut"):
                n = mp["cut"]
            elif ty == "zoom" and mp.get("zoom"):
                n = mp["zoom"]
        if soft and n in SOFT:
            n = SOFT[n]
        if n and n not in names:
            n = "pop" if "pop" in names else None
        if not n:
            continue
        need = {"it": 3, "vua": 2, "nhieu": 1}.get(density, 2)
        if pr < need and not (density == "vua" and pr == 1):
            continue
        picks.append((e.get("start", 0), pr, i, n))
    # giãn cách: không 2 âm thanh bắt đầu sát nhau (giữ cái quan trọng hơn); mật độ vừa: chữ phụ cách nhau ≥ 2,5s
    taken = [(e.get("start", 0)) for e in els if e and e.get("sfx") and not overwrite]
    last_minor = -9.0
    for t0, pr, i, n in sorted(picks, key=lambda x: (-x[1], x[0])):
        if any(abs(t0 - t1) < 0.35 for t1 in taken):
            continue
        if density == "vua" and pr == 1:
            if any(abs(t0 - t1) < 2.5 for t1 in taken):
                continue
        els[i]["sfx"] = n
        if n in LOUD and "sfxVolume" not in els[i]:
            els[i]["sfxVolume"] = LOUD[n]
        taken.append(t0)
    plan["elements"] = els
    if joins:
        plan["joinSfx"] = (cfg.get("map") or {}).get("cut") or (cfg.get("joins", True) if isinstance(cfg.get("joins", True), (bool, str)) else True)
    plan, _ = thin(plan, density, style)
    return plan


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] != "ds":
        from tiendo import stop_guard
        stop_guard(Path(a[1]).resolve())
    if a[:1] == ["ds"]:
        lib = library()
        for c, label in CATS.items():
            xs = [x for x in lib if x["cat"] == c]
            if xs:
                print(f"\n{label}:")
                for x in xs:
                    print(f"  {x['name']:16s} {x['desc']} — {x.get('use', '')}")
    elif a[:1] == ["giam"] and len(a) > 1:
        f = Path(a[1]).resolve()
        plan = json.loads((f / "plan.json").read_text(encoding="utf-8"))
        dens = "it" if "--it" in a else "nhieu" if "--nhieu" in a else "vua"
        n0 = len(events(plan))
        plan, n = thin(plan, dens)
        (f / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Giảm âm thanh hiệu ứng: {n0} -> {n0 - n} tiếng (bỏ {n}, mật độ {dens}).")
    elif a[:1] == ["tu-gan"] and len(a) > 1:
        f = Path(a[1]).resolve()
        plan = json.loads((f / "plan.json").read_text(encoding="utf-8"))
        before = sum(1 for e in plan.get("elements", []) if e.get("sfx"))
        dens = "it" if "--it" in a else "nhieu" if "--nhieu" in a else "vua"
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from phongcach import apply as apply_style
        st = apply_style(f, json.loads(json.dumps(plan))).get("style") or {}
        plan = auto(plan, dens, "--ghi-de" in a, "--khong-chuyen-canh" not in a, st)
        (f / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        after = sum(1 for e in plan.get("elements", []) if e.get("sfx"))
        print(f"Đã gán âm thanh: {after} element có âm thanh (trước {before}); chuyển cảnh: {'có' if plan.get('joinSfx') else 'không'}.")
    else:
        sys.exit(__doc__)
